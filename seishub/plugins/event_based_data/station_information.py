#!/usr/bin/env python
# -*- coding: utf-8 -*-
from seishub.core.core import Component, implements
from seishub.core.exceptions import NotFoundError, InvalidObjectError, \
    InternalServerError
from seishub.core.packages.interfaces import IMapper

from obspy.core import UTCDateTime
from obspy.xseed import Parser
import os

from table_definitions import ChannelMetadataTable
from util import check_if_file_exist_in_db, write_string_to_filesystem, \
    add_or_update_channel, add_filepath_to_database


class StationInformationUploader(Component):
    """
    Upload station information data. The actual database will only keep track
    of the filenames and the files themselves will be stored in a folder
    structure on the hard drive.

    Can currently deal with SEED, XSEED and RESP files.

    The full upload URL looks like this:

    SEISHUB_SERVER/event_based_data/station/upload

    Waveforms will be stored in the path specified in the config file at:
        [event_based_data] station_filepath.

    Every file will be named according to the following schema. Not existent
    network or station codes will be replaced with "XX". It will always be
    named after the first channel in the file.

        network/network.station.location.channel-year_month

    If necessary, a ".1", ".2", ... will be appended to the filename if many
    files close to one another in time are stored.
    """
    implements(IMapper)

    package_id = "event_based_data"
    version = "0.0.0."
    mapping_url = "/event_based_data/station/upload"

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
        request.content.seek(0, 0)
        data = request.content.read()
        # Check if file exists. Checksum is returned otherwise. Raises on
        # failure.
        md5_hash = check_if_file_exist_in_db(data, self.env)

        # Attempt to read as a SEED/XSEED file.
        request.content.seek(0, 0)
        channels = self._read_SEED(data)
        request.content.seek(0, 0)
        # Otherwise attempt to read as a RESP file.
        if channels is False:
            channels = self._read_RESP(request.content)
        # Otherwise raise an Error.
        if channels is False:
            msg = "Could not read the station information file."
            raise InvalidObjectError(msg)

        network = channels[0]["network"]

        filename = os.path.join(self.env.config.get("event_based_data",
            "station_filepath"), network,
            ("{network}.{station}.{location}.{channel}-"
            "{year}_{month}"))
        filename = filename.format(network=network,
            station=channels[0]["station"], location=channels[0]["location"],
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
                    md5_hash)
            # Loop over all channels.
            for channel in channels:
                # Add the channel if it does not already exists, or update the
                # location or just return the existing station. In any case a
                # channel column object will be returned.
                channel_row, old_channel_row = add_or_update_channel(session,
                    channel["network"], channel["station"],
                    channel["location"], channel["channel"],
                    channel["latitude"], channel["longitude"],
                    channel["elevation"])

                # Now add information about the time span of the current
                # channel information.
                if hasattr(channel["end_date"], "datetime"):
                    end_date = channel["end_date"].datetime
                else:
                    end_date = None
                metadata = ChannelMetadataTable(channel_id=channel_row.id,
                    filepath_id=filepath.id,
                    starttime=channel["start_date"].datetime,
                    endtime=end_date,
                    format=channel["format"])
                session.add(metadata)

                session.commit()
        except Exception, e:
            # Rollback session.
            session.rollback()

            # Try to rollback all changes made to the database. This is
            # unfortunately rather messy.
            try:
                session.delete(filepath)
                session.commit()
            # Possible if the exception occured before the object was created.
            except UnboundLocalError:
                pass
            except Exception, e:
                msg = "Trouble rolling back the filepath commit. " + e.message
                self.env.log.error(msg)
                raise InternalServerError(msg)
                pass

            # Delete the channel row and restore the old one if one exists.
            try:
                session.delete(channel_row)
                if old_channel_row is not None:
                    session.add(old_channel_row)
                session.commit()
            # Possible if the exception occured before the object was created.
            except UnboundLocalError:
                pass
            except Exception, e:
                msg = "Trouble rolling back the channel commit. " + e.message
                self.env.log.error(msg)
                raise InternalServerError(msg)

            # This should usually never be committed as it is the last thing
            # that can occur and thus if something went wrong it did before it
            # got added to the database. Just delete in any case.
            try:
                session.delete(metadata)
                session.commit()
            # This is to be expected as metadata will most likely not exist.
            except UnboundLocalError:
                pass
            # This should not happen.
            except Exception, e:
                msg = "Trouble rolling back the metadata commit. " + e.message
                self.env.log.error(msg)
                raise InternalServerError(msg)
            session.close()

            # Remove the file if something failes..
            os.remove(filename)
            msg = e.message + " Rolling back all changes."
            raise InternalServerError(msg)
        session.close()

    def _read_RESP(self, string_io):
        """
        Attempts to read the file as a RESP file. Returns False if no channels
        are found.
        """
        def _parse_time_string(time_string):
            """
            Helper function to parser the time strings.
            """
            if not time_string[:4].isdigit():
                return None
            year, julday, time = time_string.split(",")
            hour, minute, second = time.split(":")
            year, julday, hour, minute, second = map(int, (year, julday, hour,
                minute, second))
            time = UTCDateTime(year=year, julday=julday, hour=hour,
                minute=minute, second=second)
            return time
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
                        "format": "RESP",
                        "start_date": current_startdate,
                        "end_date": current_enddate}
                    channels.append(channel)
                # Set to None again to start the next round.
                current_network = current_station = current_location = \
                    current_channel = current_startdate = current_enddate = \
                    None
        if len(channels) == 0:
            return False
        return channels

    def _read_SEED(self, string_io):
        """
        Attempt to read the file as a SEED file. If it not a valid SEED file,
        it will return False.
        """
        try:
            p = Parser(string_io)
        except:
            return False
        if len(str(p)) == 0:
            return False
        channels = p.getInventory()["channels"]
        for channel in channels:
            channel_id = channel.pop("channel_id")
            net, sta, loc, cha = channel_id.split(".")
            channel["network"] = net
            channel["station"] = sta
            channel["location"] = loc
            channel["channel"] = cha
            channel["start_date"] = channel["start_date"]
            channel["end_date"] = channel["end_date"]
            location = p.getCoordinates(channel_id)
            channel["latitude"] = location["latitude"]
            channel["longitude"] = location["longitude"]
            channel["elevation_in_m"] = location["elevation"]
            channel["format"] = p._format
        return channels
