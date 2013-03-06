#!/usr/bin/env python
# -*- coding: utf-8 -*-
from seishub.core.core import Component, implements
from seishub.core.exceptions import InvalidObjectError, InternalServerError, \
    InvalidParameterError, NotFoundError
from seishub.core.packages.interfaces import IMapper
from seishub.core.db.util import formatResults

from obspy import read, UTCDateTime
from obspy.core.util import NamedTemporaryFile
import os
import sqlalchemy
from StringIO import StringIO

from table_definitions import ChannelObject, WaveformChannelObject
from util import check_if_file_exist_in_db, write_string_to_filesystem, \
    add_filepath_to_database, add_or_update_channel, get_all_tags, \
    event_exists, get_station_id

lowercase_true_strings = ("true", "yes", "y")


class WaveformMapper(Component):
    """
    Upload waveform data. The actual database will only keep track of the
    filenames and the files themselves will be stored in a folder structure on
    the hard drive.

    The POST upload URL is SEISHUB_SERVER/event_based_data/waveform/upload. An
    event_resource_name needs to be given and must correspond to an event
    in the database. Only event bound data can currently be uploaded.

    A full upload URL can look like this:

    SEISHUB_SERVER/event_based_data/waveform?event=EVENT_NAME

    By default the data will be assumed to be real data. Passing
    synthetic=true to the URL will make it a synthetic waveform.

    You can furthermore add a tag to any waveform making it easier to identify
    it later on. Simple use tag=SOME_TAG to give a short description. Tags have
    to be unique per channel id and event. Also only one waveform per channel
    can have no associated tag. This, per convention, should be the raw data
    stream.

    Waveforms will be stored in the path specified in the config file at:
        [event_based_data] waveform_filepath

    Every file will be named according to the following schema. Not existent
    network or station codes will be replaced with "XX". It will always be
    named after the first trace in the file.

        event_id/network.station.location.channel-year_month_day_hour

    If necessary, a ".1", ".2", ... will be appended to the filename if many
    files close to one another in time are stored.


    It is also possible to not upload the data but just tell SeisHub where it
    can be found in the form of a file url. The file url needs to be accessible
    from the SeisHub server - it is usually a good idea to use absolute
    filepaths.. This is useful if you want to leave the files where they are
    right now and just index them inside the database.

    SEISHUB_SERVER/event_based_data/waveform?event=EVENT_NAME&index_file=FILE

    Take care of correctly encoding the URL, e.g. "/" is encoded as "%2F".

    You can use urllib.urlencode() for that task:

    >>> import urllib
    >>> base_url = "SEISHUB_SERVER/event_based_data/waveform"
    >>> filepath = "/example/data/example_file.mseed"
    >>> params = {"event": "EVENT_NAME", "index_file", filepath}
    >>> url = base_url + "?" + urllib.urlencode(params)
    >>> print url
    ...?event=EVENT_NAME&index_file=%2Fexample%2Fdata%2Fexample_file.mseed
    """
    implements(IMapper)

    package_id = "event_based_data"
    version = "0.0.0."
    mapping_url = "/event_based_data/waveform"

    def process_GET(self, request):
        """
        Function that will be called upon receiving a GET request for the
        aforementioned URL.
        """
        # Parse the given parameters.
        event_id = request.args0.get("event", None)
        channel_id = request.args0.get("channel_id", None)
        tag = request.args0.get("tag", "")
        format = request.args0.get("format", None)

        acceptable_formats = ["mseed", "sac", "gse2", "segy", "raw"]
        if format and format.lower() not in acceptable_formats:
            msg = "'%s' is an unsupported format. Supported formats: %s" % \
                (format, ", ".join(acceptable_formats))
            raise InvalidParameterError(msg)

        # An event id is obviously needed.
        if event_id is None:
            msg = ("No event parameter passed. Every waveform "
                "is bound to an existing event.")
            raise InvalidParameterError(msg)

        if event_id is not None and not event_exists(event_id, self.env):
            msg = "The given event resource name '%s' " % event_id
            msg += "is not known to SeisHub."
            raise InvalidParameterError(msg)

        if channel_id is None and event_id is not None:
            return self.getListForEvent(event_id, request)

        if channel_id is None:
            msg = ("To download a waveform, 'channel_id' to be specified.")
            raise InvalidParameterError(msg)

        split_channel = channel_id.split(".")
        if len(split_channel) != 4:
            msg = "Invalid 'channel_id'. Needs to be NET.STA.LOC.CHAN."
            raise InvalidParameterError(msg)

        network, station, location, channel = split_channel

        session = self.env.db.session(bind=self.env.db.engine)
        station_id = get_station_id(network, station, session)
        if station_id is False:
            session.close()
            msg = "Could not find station %s.%s in the database" % \
                (network, station)
            raise InvalidParameterError(msg)

        query = session.query(WaveformChannelObject)\
            .join(ChannelObject, ChannelObject.station_id == station_id)\
            .filter(WaveformChannelObject.event_resource_id == event_id)\
            .filter(WaveformChannelObject.tag == tag)\
            .filter(ChannelObject.location == location)\
            .filter(ChannelObject.channel == channel)

        try:
            result = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            session.close()
            msg = "No matching data found in the database."
            raise NotFoundError(msg)

        if format and format.lower() == "raw":
            with open(result.filepath.filepath, "rb") as open_file:
                data = open_file.read()
            return data

        chan = result.channel
        stat = chan.station
        network = stat.network
        station = stat.station
        location = chan.location
        channel = chan.channel
        starttime = UTCDateTime(result.starttime) if result.starttime else None
        endtime = UTCDateTime(result.endtime) if result.endtime else None
        default_format = result.format

        # Read and filter the file.
        st = read(result.filepath.filepath).select(network=network,
            station=station, location=location, channel=channel)
        session.close()

        # Now attempt to find the correct trace in case of more then one trace.
        # This should enable multicomponent files.
        selected_trace = None
        for tr in st:
            if (starttime and abs(tr.stats.starttime - starttime) > 1) or \
                    (endtime and abs(tr.stats.endtime - endtime) > 1):
                continue
            selected_trace = tr
            break

        if selected_trace is None:
            msg = "Could not find the corresponding waveform file."
            raise InternalServerError(msg)

        # XXX: Fix some ObsPy modules to be able to write to memory files.
        tempfile = NamedTemporaryFile()
        if format:
            default_format = format
        selected_trace.write(tempfile.name, format=default_format)
        with open(tempfile.name, "rb") as open_file:
            data = open_file.read()
        tempfile.close()
        os.remove(tempfile.name)
        return data

    def getListForEvent(self, event_id, request):
        # Get all waveform channels corresponding to that id.
        session = self.env.db.session(bind=self.env.db.engine)
        query = session.query(WaveformChannelObject)\
            .filter(WaveformChannelObject.event_resource_id == event_id)\
            .all()
        result = []
        for q in query:
            chan = q.channel
            stat = chan.station
            result.append({
                "network": stat.network,
                "station": stat.station,
                "location": chan.location,
                "channel": chan.channel,
                "filepath_id": q.filepath_id,
                "tag": q.tag,
                "starttime": q.starttime.isoformat(),
                "endtime": q.endtime.isoformat(),
                "sampling_rate": q.sampling_rate,
                "format": q.format,
                "is_synthetic": q.is_synthetic})

        result = formatResults(request, result)
        return result

    def process_POST(self, request):
        """
        Function that will be called upon receiving a POST request for the
        aforementioned URL.
        """
        # Parse the given parameters.
        event_id = request.args0.get("event", None)
        is_synthetic = request.args0.get("synthetic", None)
        tag = request.args0.get("tag", "")
        if isinstance(is_synthetic, basestring) and \
                is_synthetic.lower() in lowercase_true_strings:
            is_synthetic = True
        else:
            is_synthetic = False

        # Every waveform MUST be bound to an event.
        if event_id is None:
            msg = ("No event parameter passed. Every waveform "
                "must be bound to an existing event.")
            raise InvalidParameterError(msg)

        if not event_exists(event_id, self.env):
            msg = "The given event resource name '%s' " % event_id
            msg += "is not known to SeisHub."
            raise InvalidParameterError(msg)

        # There are two possibilities for getting data inside the database:
        # upload the file directly to SeisHub or just give a file URL that the
        # server can find.
        filename = request.args0.get("index_file", None)
        # If the 'index_file' parameter is not given, assume the file will be
        # directly uploaded.
        if filename is None:
            waveform_data = request.content
            waveform_data.seek(0, 0)
            file_is_managed_by_seishub = True
        else:
            filename = os.path.abspath(filename)
            if not os.path.exists(filename) or \
                    not os.path.isfile(filename):
                msg = "File '%s' cannot be found by the SeisHub server." % \
                    filename
                raise InvalidParameterError(msg)
            with open(filename, "rb") as open_file:
                waveform_data = StringIO(open_file.read())
            waveform_data.seek(0, 0)
            file_is_managed_by_seishub = False

        # Check if file exists. Checksum is returned otherwise. Raises on
        # failure.
        data = waveform_data.read()
        waveform_data.seek(0, 0)
        md5_hash = check_if_file_exist_in_db(data, self.env)

        msg = ("The data does not appear to be a valid waveform file. Only "
               "data readable by ObsPy is acceptable.")
        # Only valid waveforms files will be stored in the database. Valid is
        # defined by being readable by ObsPy.
        try:
            st = read(waveform_data)
        except:
            raise InvalidObjectError(msg)

        # Replace network, station and channel codes with placeholders if they
        # do not exist. Location can be an empty string.
        network = st[0].stats.network if st[0].stats.network else "XX"
        station = st[0].stats.station if st[0].stats.station else "XX"
        location = st[0].stats.location
        channel = st[0].stats.channel if st[0].stats.channel else "XX"

        # Check if the tag is valid, e.g. that it fulfulls the constraints of
        # being unique per channel_id and event.
        tags = get_all_tags(network, station, location, channel, event_id,
            self.env)
        if tag in tags:
            msg = "Tag already exists for the given channel id and event."
            raise InvalidParameterError(msg)

        if file_is_managed_by_seishub is True:
            # Otherwise create the filename for the file, and check if it
            # exists.
            filename = os.path.join(self.env.config.get("event_based_data",
                "waveform_filepath"), event_id,
                ("{network}.{station}.{location}.{channel}-"
                "{year}_{month}_{day}_{hour}"))
            t = st[0].stats.starttime
            filename = filename.format(network=network, station=station,
                channel=channel, location=location, year=t.year, month=t.month,
                day=t.day, hour=t.hour)

            # Write the data to the filesystem. The final filename is returned.
            filename = write_string_to_filesystem(filename, data)

        # Use only one session to be able to take advantage of transactions.
        session = self.env.db.session(bind=self.env.db.engine)

        # Wrap in try/except and rollback changes in case something fails.
        try:
            # Add information about the uploaded file into the database.
            filepath = add_filepath_to_database(session, filename, len(data),
                    md5_hash, is_managed_by_seishub=file_is_managed_by_seishub)

            # Loop over all traces in the file.
            for trace in st:
                stats = trace.stats

                # Extract coordinates if it is a sac file. Else set them to
                # None.
                if hasattr(stats, "sac"):
                    latitude = stats.sac.stla
                    longitude = stats.sac.stlo
                    elevation = stats.sac.stel
                    local_depth = stats.sac.stdp
                    # Treat local_depth seperately. If it is not given, assume
                    # it is 0.
                    if local_depth == -12345.0:
                        local_depth = 0
                    # If any is invalid, assume all are.
                    if -12345.0 in [latitude, longitude, elevation] or \
                            None in [latitude, longitude, elevation]:
                        latitude, longitude, elevation, local_depth = \
                            [None] * 4
                else:
                    latitude, longitude, elevation, local_depth = [None] * 4

                # Add the channel if it does not already exists, or update the
                # location or just return the existing station. In any case a
                # channel column object will be returned.
                channel_row = add_or_update_channel(session,
                    stats.network, stats.station, stats.location,
                    stats.channel, latitude, longitude, elevation, local_depth)

                # Add the current waveform channel as well.
                waveform_channel = WaveformChannelObject(
                    channel=channel_row, filepath=filepath,
                    event_resource_id=event_id,
                    starttime=stats.starttime.datetime,
                    endtime=stats.endtime.datetime, tag=tag,
                    sampling_rate=stats.sampling_rate, format=stats._format,
                    is_synthetic=is_synthetic)
                session.add(waveform_channel)

                session.commit()
        except Exception, e:
            # Rollback session.
            session.rollback()
            session.close()

            # Remove the file if something failes..
            if file_is_managed_by_seishub:
                os.remove(filename)
            msg = e.message + " - Rolling back all changes."
            raise InternalServerError(msg)
        session.close()
