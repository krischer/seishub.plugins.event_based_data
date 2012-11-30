#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shared utility function.

:copyright:
    Lion Krischer (krischer@geophysik.uni-muenchen.de), 2012
:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html)
"""
from seishub.core.exceptions import DuplicateObjectError, InternalServerError

import copy
import datetime
import hashlib
import os

from table_definitions import ChannelObject, FilepathObject


def check_if_file_exist_in_db(data, env):
    """
    Checks if a file with the same md5 checksum exists in the filepaths table.
    Raises an appropriate error if it does not exist. Otherwise the md5 hash is
    returned.

    :type data: String
    :param data: The file as a string.
    :type env: seishub.core.Environment
    :param env: The current SeisHub environment
    """
    md5_hash = hashlib.md5(data).hexdigest()

    session = env.db.session(bind=env.db.engine)
    query = session.query(FilepathObject.md5_hash).filter(
        FilepathObject.md5_hash == md5_hash)
    count = query.count()
    session.close()
    if count != 0:
        msg = "This file already exists in the database."
        raise DuplicateObjectError(msg)
    return md5_hash


def write_string_to_filesystem(filename, string):
    """
    Takes a given string and writes it to the given filename. Any intermediate
    directories will be created in case they do not exist. If the file already
    exists, an increasing integer will be appended to it until a non-take
    filename is found.

    Returns the final filename.
    """
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
        open_file.write(string)
    return filename


def add_filepath_to_database(open_session, filepath, filesize, md5_hash):
    """
    Add information about a filepath to the database. Expects an open
    SQLAlchemy session.

    Returns the Column object.
    """
    # Add information about the uploaded file into the database.
    filepath = FilepathObject(filepath=filepath, size=filesize,
        mtime=datetime.datetime.now(), md5_hash=md5_hash)
    open_session.add(filepath)
    open_session.commit()
    return filepath


def add_or_update_channel(open_session, network, station, location, channel,
    latitude, longitude, elevation):
    """
    Adds the channel with the given parameters. If it already exists and does
    not yet have coordinates, those will be added.

    In any case the object from SQLAlchemy's ORM will be returned. It
    furthermore returns the old version of the channel row. Useful for rolling
    back changes if something goes bad later on.
    """
    # Find the potentially already existing channel.
    query = open_session.query(ChannelObject)\
        .filter(ChannelObject.network == network)\
        .filter(ChannelObject.station == station)\
        .filter(ChannelObject.location == location)\
        .filter(ChannelObject.channel == channel)
    if query.count() == 0:
        channel = ChannelObject(network=network,
            station=station, channel=channel,
            location=location)
        old_channel = None
    # Also update already existent channels with location
    # information.
    elif query.count() == 1:
        channel = query.first()
        old_channel = copy.copy(channel)
    else:
        # This should never happen. Just a safety measure. Should
        # already be covered by constraints within the database.
        msg = "Duplicate channel in the channel database."
        raise InternalServerError(msg)
    if latitude and longitude and elevation and (not channel.latitude or
        not channel.longitude or not channel.elevation_in_m):
        channel.latitude = latitude
        channel.longitude = longitude
        channel.elevation_in_m = elevation
    open_session.add(channel)
    open_session.commit()

    return channel, old_channel
