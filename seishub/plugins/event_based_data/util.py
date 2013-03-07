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
from seishub.core.exceptions import DuplicateObjectError

import datetime
import hashlib
import os
import sqlalchemy

from table_definitions import ChannelObject, FilepathObject, StationObject, \
    WaveformChannelObject


def event_exists(event_name, env):
    """
    Checks if an event with the given name exists in the database.

    Returns True or False.

    :type event_name: String
    :param event_name: The name of the event.
    :type env: seishub.core.Environment
    :param env: The current SeisHub environment
    """
    # Get the event.
    session = env.db.session(bind=env.db.engine)
    event_view = sqlalchemy.Table("/event_based_data/event", env.db.metadata,
        autoload=True)
    query = session.query(event_view.columns["resource_name"]).filter(
        event_view.columns["resource_name"] == event_name)
    count = query.count()
    session.close()

    return bool(count)


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


def get_station_id(network, station, session):
    """
    Get the station_id for a given network and station combination. Requires an
    open session.
    """
    # XXX: Figure out how to do this properly with joins and the like.
    query = session.query(StationObject.id)\
        .filter(StationObject.network == network)\
        .filter(StationObject.station == station)
    try:
        station_id = query.one()[0]
    except sqlalchemy.orm.exc.NoResultFound:
        return False
    return station_id


def get_all_tags(network, station, location, channel, event_id, env):
    """
    Helper function returning a list of all tags for a given channel and event
    combination. Does not check if the event actually exists, just querys the
    database for the requested combination.
    """
    session = env.db.session(bind=env.db.engine)

    station_id = get_station_id(network, station, session)
    if station_id is False:
        return []

    query = session.query(WaveformChannelObject.tag)\
        .join(ChannelObject, ChannelObject.station_id == station_id)\
        .filter(WaveformChannelObject.event_resource_id == event_id)\
        .filter(ChannelObject.location == location)\
        .filter(ChannelObject.channel == channel)
    return [_i[0] for _i in query.all()]


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


def add_filepath_to_database(open_session, filepath, filesize, md5_hash,
        is_managed_by_seishub):
    """
    Add information about a filepath to the database. Expects an open
    SQLAlchemy session.

    Returns the Column object.
    """
    filepath = os.path.abspath(filepath)
    # Add information about the uploaded file into the database.
    filepath = FilepathObject(filepath=filepath, size=filesize,
        mtime=datetime.datetime.now(), md5_hash=md5_hash,
        is_managed_by_seishub=is_managed_by_seishub)
    open_session.add(filepath)
    return filepath


def add_or_update_channel(open_session, network, station, location, channel,
        latitude, longitude, elevation, local_depth, force_update=False):
    """
    Adds the channel with the given parameters. It will add station and channel
    objects as appropriate. Will add the coordinates to the station if it does
    not have coordinates yet.

    Returns the channel object from SQLAlchemy's ORM.

    :param force_update: If True, always overwrite everything, otherwise only
        write previously not-existing values.
    """
    # Find the potentially already existing station in the database, otherwise
    # create it. In any case, the station_object variable will contain the
    # current station at the end of the block.
    station_query = open_session.query(StationObject)\
        .filter(StationObject.network == network)\
        .filter(StationObject.station == station)
    if station_query.count() == 0:
        station_object = StationObject(network=network, station=station)
    else:
        station_object = station_query.one()

    # Check if the channel already exists in the database, if not create it and
    # set the correct foreign key.
    channel_query = open_session.query(ChannelObject).join(StationObject)\
        .filter(StationObject.network == network)\
        .filter(StationObject.station == station)\
        .filter(ChannelObject.location == location)\
        .filter(ChannelObject.channel == channel)
    if channel_query.count() == 0:
        channel_object = ChannelObject(channel=channel, location=location,
            station=station_object)
    else:
        channel_object = channel_query.one()

    # Update only if either not set or force_update is True
    if latitude is not None and (not station_object.latitude or force_update is
            True):
        station_object.latitude = latitude
    if longitude is not None and (not station_object.longitude or force_update
            is True):
        station_object.longitude = longitude
    if elevation is not None and (not station_object.elevation_in_m or
            force_update is True):
        station_object.elevation_in_m = elevation
    if local_depth is not None and (not station_object.local_depth_in_m or
            force_update is True):
        station_object.local_depth_in_m = local_depth

    # Add both to the open session.
    open_session.add(station_object)
    open_session.add(channel_object)

    return channel_object
