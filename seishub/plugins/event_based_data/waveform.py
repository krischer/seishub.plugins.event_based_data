#!/usr/bin/env python
# -*- coding: utf-8 -*-
from seishub.core.core import Component, implements
from seishub.core.exceptions import NotFoundError, InvalidObjectError, \
    InternalServerError, InvalidParameterError
from seishub.core.packages.interfaces import IMapper

from obspy.core import read
import os
from sqlalchemy import Table

from table_definitions import WaveformChannelObject
from util import check_if_file_exist_in_db, write_string_to_filesystem, \
    add_filepath_to_database, add_or_update_channel

lowercase_true_strings = ("true", "yes", "y")


class WaveformUploader(Component):
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
    is_synthetic=true to the URL will make it a synthetic waveform.

    Waveforms will be stored in the path specified in the config file at:
        [event_based_data] waveform_filepath

    Every file will be named according to the following schema. Not existent
    network or station codes will be replaced with "XX". It will always be
    named after the first trace in the file.

        network/station/network.station.location.channel-year_month_day_hour

    If necessary, a ".1", ".2", ... will be appended to the filename if many
    files close to one another in time are stored.
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
        # Get not allowed for this mapper. Return 404.
        raise NotFoundError("GET not supported for this URL.")

    def process_POST(self, request):
        """
        Function that will be called upon receiving a POST request for the
        aforementioned URL.
        """
        # Parse the given parameters.
        event_id = request.args0.get("event", None)
        is_synthetic = request.args0.get("is_synthetic", None)
        if isinstance(is_synthetic, basestring) and \
            is_synthetic.lower() in lowercase_true_strings:
            is_synthetic = True
        else:
            is_synthetic = False

        # Every waveform MUST be bound to an event.
        if event_id is None:
            msg = ("No event_resource_name parameter passed. Every waveform "
                "must be bound to an existing event.")
            raise InvalidParameterError(msg)

        # Check if the event actually exists in the database.
        session = self.env.db.session(bind=self.env.db.engine)
        event_view = Table("/event_based_data/event", request.env.db.metadata,
                            autoload=True)
        query = session.query(event_view.columns["resource_name"]).filter(
            event_view.columns["resource_name"] == event_id)
        if query.count() == 0:
            msg = "The given event resource name '%s' " % event_id
            msg += "is not known to SeisHub."
            raise InvalidParameterError(msg)

        request.content.seek(0, 0)
        data = request.content.read()

        # Check if file exists. Checksum is returned otherwise. Raises on
        # failure.
        md5_hash = check_if_file_exist_in_db(data, self.env)
        request.content.seek(0, 0)

        msg = ("The attached content does not appear to be a valid waveform "
               "file. Only data readable by ObsPy is acceptable.")
        # Only valid waveforms files will be stored in the database. Valid is
        # defined by being readable by ObsPy.
        try:
            st = read(request.content)
        except:
            raise InvalidObjectError(msg)
        # Also raise if it does not contain any waveform data.
        if len(st) == 0:
            raise InvalidObjectError(msg)

        # Replace network, station and channel codes with placeholders if they
        # do not exist. Location can be an empty string.
        network = st[0].stats.network if st[0].stats.network else "XX"
        station = st[0].stats.station if st[0].stats.station else "XX"
        location = st[0].stats.location
        channel = st[0].stats.channel if st[0].stats.channel else "XX"

        # Otherwise create the filename for the file, and check if it exists.
        filename = os.path.join(self.env.config.get("event_based_data",
            "waveform_filepath"), network, station,
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
                    md5_hash, is_managed_by_seishub=True)

            # Loop over all traces in the file.
            for trace in st:
                stats = trace.stats

                # Extract coordinates if it is a sac file. Else set them to
                # None.
                if hasattr(stats, "sac"):
                    latitude = stats.sac.stla
                    longitude = stats.sac.stlo
                    elevation = stats.sac.stel
                    # If any is invalid, assume all are.
                    if -12345.0 in [latitude, longitude, elevation] or \
                        None in [latitude, longitude, elevation]:
                        latitude, longitude, elevation = None
                else:
                    latitude, longitude, elevation = None

                # Add the channel if it does not already exists, or update the
                # location or just return the existing station. In any case a
                # channel column object will be returned.
                channel_row = add_or_update_channel(session,
                    stats.network, stats.station, stats.location,
                    stats.channel, latitude, longitude, elevation)

                # Add the current waveform channel as well.
                waveform_channel = WaveformChannelObject(
                    channel=channel_row, filepath=filepath,
                    event_resource_id=event_id,
                    starttime=stats.starttime.datetime,
                    endtime=stats.endtime.datetime,
                    sampling_rate=stats.sampling_rate, format=stats._format,
                    is_synthetic=is_synthetic)
                session.add(waveform_channel)

                session.commit()
        except Exception, e:
            # Rollback session.
            session.rollback()
            session.close()

            # Remove the file if something failes..
            os.remove(filename)
            msg = e.message + " - Rolling back all changes."
            raise InternalServerError(msg)
        session.close()
