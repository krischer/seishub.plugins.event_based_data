#!/usr/bin/env python
# -*- coding: utf-8 -*-
from seishub.core.core import Component, implements
from seishub.core.exceptions import NotFoundError, InvalidObjectError, \
    InternalServerError, InvalidParameterError
from seishub.core.packages.interfaces import IMapper
from seishub.core.db.util import formatResults

import json
from obspy.core import UTCDateTime
from obspy.xseed import Parser
import os
from sqlalchemy.exc import IntegrityError
import StringIO

from table_definitions import ChannelMetadataObject, StationObject
from util import check_if_file_exist_in_db, write_string_to_filesystem, \
    add_or_update_channel, add_filepath_to_database


class StationListMapper(Component):
    """
    Generates a list of available seismic stations.
    """
    implements(IMapper)

    package_id = "event_based_data"
    version = "0.0.0."
    mapping_url = "/event_based_data/stations/getList"

    def process_GET(self, request):
        """
        Function that will be called upon receiving a GET request for the
        aforementioned URL.

        The 'format' argument supports xml, xhtml, json, and geojson and will
        output the appropriate type.
        """
        # XXX: This is likely not optimal.
        session = self.env.db.session(bind=self.env.db.engine)
        query = session.query(StationObject).order_by(StationObject.network)\
            .order_by(StationObject.station).all()
        query = [{
            "id": i.id,
            "network": i.network,
            "station": i.station,
            "latitude": i.latitude,
            "longitude": i.longitude,
            "elevation_in_m": i.elevation_in_m,
            "local_depth_in_m": i.local_depth_in_m,
            "channels": [{"channel": j.channel}
                for j in i.channel]} for i in query]

        # Encode geojson manually, let the rest be handled by a convenience
        # method.
        formats = request.args.get("format", [])
        if "geojson" in formats:
            result = {"type": "FeatureCollection",
                "features": []}
            for item in query:
                feature = {"type": "Feature",
                    "geometry": {"type": "Point",
                        "coordinates": [item["longitude"], item["latitude"]]},
                    "properties": {
                        "elevation_in_m": item["elevation_in_m"],
                        "latitude": item["latitude"],
                        "longitude": item["longitude"],
                        "network": item["network"],
                        "station": item["station"],
                        "local_depth_in_m": item["local_depth_in_m"],
                        "channels": ", ".join([_i["channel"]
                            for _i in item["channels"]])},
                    "id": "%s.%s" % (item["network"], item["station"])}
                result["features"].append(feature)
            result = json.dumps(result)
            request.setHeader('content-type',
                'application/json; charset=UTF-8')
        else:
            result = formatResults(request, query)
        return result


class StationInformationUploader(Component):
    """
    Upload station information data. The actual database will only keep track
    of the filenames and the files themselves will be stored in a folder
    structure on the hard drive.

    Can currently deal with SEED, XSEED and RESP files.

    The full upload URL looks like this:

    SEISHUB_SERVER/event_based_data/station

    Waveforms will be stored in the path specified in the config file at:
        [event_based_data] station_filepath.

    Every file will be named according to the following schema. Not existent
    network or station codes will be replaced with "XX". It will always be
    named after the first channel in the file.

        network/network.station.location.channel-year_month

    If necessary, a ".1", ".2", ... will be appended to the filename if many
    files close to one another in time are stored.

    It is also possible to not upload the data but just tell SeisHub where it
    can be found in the form of a file url. The file url needs to be accessible
    from the SeisHub server - it is usually a good idea to use absolute
    filepaths.. This is useful if you want to leave the files where they are
    right now and just index them inside the database.

    SEISHUB_SERVER/event_based_data/station?index_file=FILE

    Take care of correctly encoding the URL, e.g. "/" is encoded as "%2F".

    You can use urllib.urlencode() for that task:

    >>> import urllib
    >>> base_url = "SEISHUB_SERVER/event_based_data/station"
    >>> filepath = "/example/data/example_file.seed"
    >>> params = {index_file", filepath}
    >>> url = base_url + "?" + urllib.urlencode(params)
    >>> print url
    SEISHUB_SERVER/...station?index_file=%2Fexample%2Fdata%2Fexample_file.mseed
    """
    implements(IMapper)

    package_id = "event_based_data"
    version = "0.0.0."
    mapping_url = "/event_based_data/station"

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
        # There are two possibilities for getting data inside the database:
        # upload the file directly to SeisHub or just give a file URL that the
        # server can find.
        filename = request.args0.get("index_file", None)
        # If the 'index_file' parameter is not given, assume the file will be
        # directly uploaded.
        if filename is None:
            station_data = request.content
            station_data.seek(0, 0)
            file_is_managed_by_seishub = True
        else:
            filename = os.path.abspath(filename)
            if not os.path.exists(filename) or \
                not os.path.isfile(filename):
                msg = "File '%s' cannot be found by the SeisHub server." % \
                    filename
                raise InvalidParameterError(msg)
            with open(filename, "rb") as open_file:
                station_data = StringIO.StringIO(open_file.read())
            station_data.seek(0, 0)
            file_is_managed_by_seishub = False

        # Check if file exists. Checksum is returned otherwise. Raises on
        # failure.
        data = station_data.read()
        station_data.seek(0, 0)
        md5_hash = check_if_file_exist_in_db(data, self.env)

        # Attempt to read as a SEED/XSEED file.
        station_data.seek(0, 0)
        channels = _read_SEED(station_data)
        station_data.seek(0, 0)
        # Otherwise attempt to read as a RESP file.
        if channels is False:
            channels = _read_RESP(station_data)
        # Otherwise raise an Error.
        if channels is False:
            msg = "Could not read the station information file."
            raise InvalidObjectError(msg)

        if file_is_managed_by_seishub is True:
            network = channels[0]["network"]

            filename = os.path.join(self.env.config.get("event_based_data",
                "station_filepath"), network,
                ("{network}.{station}.{location}.{channel}-"
                "{year}_{month}"))
            filename = filename.format(network=network,
                station=channels[0]["station"],
                location=channels[0]["location"],
                channel=channels[0]["channel"],
                year=channels[0]["start_date"].year,
                month=channels[0]["start_date"].month)

            # Write the data to the filesystem. The final filename is returned.
            filename = write_string_to_filesystem(filename, data)

        # Use only one session to be able to take advantage of transactions.
        session = self.env.db.session(bind=self.env.db.engine)

        # Wrap in try/except and rollback changes in case something fails.
        try:
            # Add information about the uploaded file into the database.
            filepath = add_filepath_to_database(session, filename, len(data),
                md5_hash, is_managed_by_seishub=file_is_managed_by_seishub)
            # Loop over all channels.
            for channel in channels:
                # Add the channel if it does not already exists, or update the
                # location or just return the existing station. In any case a
                # channel column object will be returned.
                channel_row = add_or_update_channel(session,
                    channel["network"], channel["station"],
                    channel["location"], channel["channel"],
                    channel["latitude"], channel["longitude"],
                    channel["elevation"], channel["local_depth"])

                # Now add information about the time span of the current
                # channel information.
                if hasattr(channel["end_date"], "datetime"):
                    end_date = channel["end_date"].datetime
                else:
                    end_date = None

                metadata = ChannelMetadataObject(channel=channel_row,
                    filepath=filepath,
                    starttime=channel["start_date"].datetime,
                    endtime=end_date,
                    format=channel["format"])
                session.add(metadata)

                session.commit()
        except Exception, e:
            # Rollback session.
            session.rollback()
            session.close()

            # Attempt to return a meaningfull error message.
            msg = ("(%s) " % e.__class__.__name__) + e.message + \
                " -- Rolling back all changes."
            # It is possible that two files with different hashes contain
            # information about exactly the same time span. In this case the
            # uniqueness constrains of the database will complain and an
            # integrity error will be raised. Catch it to give a meaningful
            # error message.
            if isinstance(e, IntegrityError) and hasattr(channel, "starttime"):
                msg = ("\nThe information for the following timespan is "
                    "already existant in the database:\n")
                msg += "%s.%s.%s.%s - %s-%s\n" % (channel["network"],
                    channel["station"], channel["location"],
                    channel["channel"], str(channel["starttime"]),
                    str(channel["endtime"]))
                msg += ("All information contained in this file will not be "
                    "added to the database.")
            # Remove the file if something failed.
            if file_is_managed_by_seishub is True:
                os.remove(filename)
            self.env.log.error(msg)
            raise InternalServerError(msg)
        session.close()


def _read_RESP(string_io):
    """
    Attempts to read the file as a RESP file. Returns False if no channels
    are found.
    """
    def _parse_time_string(datetime_string):
        """
        Helper function to parser the time strings.
        """
        # No time is often indicated with the string "No Ending Time". In
        # this case only "Time" would be passed to this function.
        if datetime_string.lower() == "time":
            return None
        dt = datetime_string.split(",")
        # Parse 2003,169
        if len(dt) == 2:
            year, julday = map(int, dt)
            return UTCDateTime(year=year, julday=julday)
        # Parse 2003,169,00:00:00.0000 and 2009,063,11
        elif len(dt) == 3:
            # Parse 2009,063,11
            if dt[2].isdigit():
                year, julday, hour = map(int, dt)
                return UTCDateTime(year=year, julday=julday, hour=hour)
            # Parse 2003,169,00:00:00.0000
            year, julday = map(int, dt[:2])
            time_split = dt[-1].split(":")
            if len(time_split) == 3:
                hour, minute, second = time_split
                # Add the seconds seperately because the constructor does
                # not accept seconds as floats.
                return UTCDateTime(year=year, julday=julday,
                    hour=int(hour), minute=int(minute)) + float(second)
            elif len(time_split) == 2:
                hour, minute = map(int, time_split)
                return UTCDateTime(year=year, julday=julday,
                    hour=int(hour), minute=int(minute))
            else:
                msg = "Unknown datetime representation %s in RESP file." \
                    % datetime_string
                raise NotImplementedError(msg)
        else:
            msg = "Unknown datetime representation %s in RESP file." % \
                datetime_string
            raise NotImplementedError(msg)

    channels = []

    # Set all to None.
    current_network = current_station = current_location = \
        current_channel = current_startdate = current_enddate = None

    for line in string_io:
        line = line.strip()
        # Station.
        if line.startswith("B050F03"):
            current_station = line.split()[-1]
        # Network
        elif line.startswith("B050F16"):
            current_network = line.split()[-1]
        # Location
        elif line.startswith("B052F03"):
            current_location = line.split()[-1]
            if current_location == "??":
                current_location = ""
        # Channel
        elif line.startswith("B052F04"):
            current_channel = line.split()[-1]
        # Startdate
        elif line.startswith("B052F22"):
            current_startdate = _parse_time_string(line.split()[-1])
        # Enddate
        elif line.startswith("B052F23"):
            current_enddate = _parse_time_string(line.split()[-1])
            if current_network is not None and \
                current_station is not None and \
                current_location is not None and \
                current_channel is not None and \
                current_startdate is not None:
                channel = {"network": current_network,
                    "station": current_station,
                    "location": current_location,
                    "channel": current_channel,
                    "latitude": None,
                    "longitude": None,
                    "elevation": None,
                    "local_depth": None,
                    "format": "RESP",
                    "start_date": current_startdate,
                    "end_date": current_enddate}
                # Some files contain the same information twice. If it is
                # within one file consider it to be ok.
                if not channel in channels:
                    channels.append(channel)
            # Set to None again to start the next round.
            current_network = current_station = current_location = \
                current_channel = current_startdate = current_enddate = \
                None
    if len(channels) == 0:
        return False
    return channels


def _read_SEED(string_io):
    """
    Attempt to read the file as a SEED file. If it not a valid SEED file,
    it will return False.
    """
    try:
        parser = Parser(string_io)
    except:
        return False
    if len(str(parser)) == 0:
        return False
    channels = parser.getInventory()["channels"]

    for channel in channels:
        channel_id = channel.pop("channel_id")
        del channel["sampling_rate"]
        net, sta, loc, cha = channel_id.split(".")
        channel["network"] = net
        channel["station"] = sta
        channel["location"] = loc
        channel["channel"] = cha
        channel["start_date"] = channel["start_date"]
        channel["end_date"] = channel["end_date"]
        location = parser.getCoordinates(channel_id)
        channel["latitude"] = location["latitude"]
        channel["longitude"] = location["longitude"]
        channel["elevation"] = location["elevation"]
        channel["local_depth"] = location["local_depth"]
        channel["format"] = parser._format
    return channels


class StationDetailMapper(Component):
    """
    Get detailed information about a station. This operations opens multiple
    files and this is potentially slow.

    Necessary parameters:
        network, station
    """
    implements(IMapper)

    package_id = "event_based_data"
    version = "0.0.0."
    mapping_url = "/event_based_data/stations/getDetails"

    def process_GET(self, request):
        network = request.args.get("network", [])[0]
        station = request.args.get("station", [])[0]
        if not station or not network:
            msg = "station and network parameters are required."
            raise InvalidObjectError(msg)
        session = self.env.db.session(bind=self.env.db.engine)
        query = session.query(StationObject)\
            .filter(StationObject.network == network)\
            .filter(StationObject.station == station)\
            .first()
        if not query:
            msg = "Station %s.%s could not be found." % (network, station)
            raise NotFoundError(msg)
        result = {
            "network_code": query.network,
            "station_code": query.station,
            "latitude": query.latitude,
            "longitude": query.longitude,
            "elevation_in_m": query.elevation_in_m,
            "local_depth_in_m": query.local_depth_in_m,
            "channels": []}
        # Also parse information about all channels.
        for channel in query.channel:
            md = channel.channel_metadata[0]
            info = {
                "channel_code": channel.channel,
                "location_code": channel.location,
                "starttime": md.starttime,
                "endtime": md.starttime,
                "format": md.format,
                "channel_filepath_id": md.filepath_id}
            result["channels"].append({"channel": info})
        print result
        return formatResults(request, [result])
