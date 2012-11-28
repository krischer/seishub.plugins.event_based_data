#!/usr/bin/env python
# -*- coding: utf-8 -*-
from seishub.core.core import Component, implements
from seishub.core.exceptions import NotFoundError, DuplicateObjectError, \
    InvalidObjectError, InternalServerError
from seishub.core.packages.interfaces import IMapper

import datetime
import hashlib
from obspy.core import read
import os

from table_definitions import FilepathsTable, ChannelsTable


class WaveformUploader(Component):
    """
    Upload waveform data. The actual database will only keep track of the
    filenames and the files themselves will be stored in a folder structure on
    the hard drive.

    They will be stored in the path specified in the config file at:
        [event_based_data] waveform_filepath

    Every file will be named according to the following schema. Not existent
    network or station codes will be replaced with "XX". It will always be
    named after the first trace in the file.

        network/station/network.station.channel-year_month_day_hour

    If necessary, a ".1", ".2", ... will be appended to the filename if many
    files close to one another in time are stored.
    """
    implements(IMapper)

    package_id = "event_based_data"
    version = "0.0.0."
    mapping_url = "/event_based_data/waveform/upload"

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

        # Read the data, calculate the md5 hash and check if the file already
        # exists.
        request.content.seek(0, 0)
        data = request.content.read()
        md5_hash = hashlib.md5(data).hexdigest()

        session = self.env.db.session(bind=self.env.db.engine)
        query = session.query(FilepathsTable.md5_hash).filter(
            FilepathsTable.md5_hash == md5_hash)
        # Check if a file with the same hash if found. If it is, raise an
        # appropriate HTTP error code.
        if query.count() != 0:
            msg = "This file already exists in the database."
            raise DuplicateObjectError(msg)
        session.close()

        # Replace network, station and channel codes with placeholders if they
        # do not exist.
        network = st[0].stats.network if st[0].stats.network else "XX"
        station = st[0].stats.station if st[0].stats.station else "XX"
        channel = st[0].stats.channel if st[0].stats.channel else "XX"

        # Otherwise create the filename for the file, and check if it exists.
        filename = os.path.join(self.env.config.get("event_based_data",
            "waveform_filepath"), network, station,
            "{network}.{station}.{channel}-{year}_{month}_{day}_{hour}")
        t = st[0].stats.starttime
        filename = filename.format(network=network, station=station,
            channel=channel, year=t.year, month=t.month, day=t.day,
            hour=t.hour)
        # If it exists, append a number. Repeat until a non taken one if found.
        if os.path.exists(filename):
            i = 1
            while True:
                new_filename = "%s.%i" % (filename, i)
                if not os.path.exists(new_filename):
                    filename = new_filename
                    break
                i += 1

        # Get the directory and if it does not exist, create it.
        directory = os.path.dirname(filename)
        if not os.path.exists(directory):
            os.makedirs(directory)
        # Write the file
        with open(filename, "wb") as open_file:
            open_file.write(data)

        # Use only one session to be able to take advantage of transactions.
        session = self.env.db.session(bind=self.env.db.engine)

        # Wrap in try/except and rollback changes in case something fails.
        try:
            # Add information about the uploaded file into the database.
            session.add(FilepathsTable(filepath=filename, size=len(data),
                mtime=datetime.datetime.now(), md5_hash=md5_hash))
            # Loop over all traces in the file.
            for trace in st:
                stats = trace.stats
                # Find the potentially already existing channel.
                query = session.query(ChannelsTable)\
                    .filter(ChannelsTable.network == stats.network)\
                    .filter(ChannelsTable.station == stats.station)\
                    .filter(ChannelsTable.location == stats.location)\
                    .filter(ChannelsTable.channel == stats.channel)
                # Some waveform formats can contain location information. This
                # should be used if applicable.
                if hasattr(st[0].stats, "sac"):
                    lat = st[0].stats.sac.stla
                    lng = st[0].stats.sac.stlo
                    ele = st[0].stats.sac.stel
                    # If any is invalid, assume all are.
                    if -12345.0 in [lat, lng, ele] or None in [lat, lng, ele]:
                        lat, lng, ele = None
                else:
                    lat, lng, stel = None
                if query.count() == 0:
                    channel = ChannelsTable(network=stats.network,
                        station=stats.station, channel=stats.channel,
                        location=stats.location)
                # Also update already existent channels with location
                # information.
                elif query.count() == 1:
                    channel = query.first()
                else:
                    # This should never happen. Just a safety measure. Should
                    # already be covered by constraints within the database.
                    msg = "Duplicate channel in the channel database."
                    raise Exception
                if lat and lng and ele and (not channel.latitude or
                    not channel.longitude or not channel.elevation_in_m):
                    channel.latitude = lat
                    channel.longitude = lng
                    channel.elevation_in_m = ele
                session.add(channel)
                session.commit()
        except Exception, e:
            # Rollback session.
            session.rollback()
            session.close()
            # Remove the file if something failes..
            os.remove(filename)
            msg = e.message + "\nRolling back changes."
            raise InternalServerError(msg)
        session.close()
