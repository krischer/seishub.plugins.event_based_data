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

from table_definitions import FilepathsTable


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

        # So far nothing has been written to the database. Do this now. If it
        # fails, roll back any database changes and delete the file.
        session = self.env.db.session(bind=self.env.db.engine)
        try:
            session.add(FilepathsTable(filepath=filename, size=len(data),
                mtime=datetime.datetime.now(), md5_hash=md5_hash))
        except Exception, e:
            # Rollback session.
            session.rollback()
            session.close()
            # Remove the file.
            os.remove(filename)
            msg = e.message + "\nRolling back changes."
            raise InternalServerError(msg)

