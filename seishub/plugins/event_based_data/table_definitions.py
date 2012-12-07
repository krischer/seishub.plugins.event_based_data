#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Table definitions for the event based data plugin. Every table is prefixed
with "ebd_" to indicate it is part of the event_based_data plugin.

:copyright:
    Lion Krischer (krischer@geophysik.uni-muenchen.de), 2012
:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html)
"""

from sqlalchemy import ForeignKey, Column, Integer, DateTime, Float, String, \
    Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import UniqueConstraint


Base = declarative_base()


class ChannelObject(Base):
    """
    Database table containing channel information.
    """
    __tablename__ = "ebd_channels"
    # Every channel can only appear once
    __table_args__ = (UniqueConstraint("station_id", "location", "channel"),
        {})
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, ForeignKey("ebd_stations.id"), nullable=False)
    location = Column(String, nullable=False, index=True)
    channel = Column(String, nullable=False, index=True)

    station = relationship("StationObject",
        backref=backref("channel", order_by=id))


class StationObject(Base):
    """
    Table containing informations about all stations. Lat/lng/depth are
    nullable because they do not necessarily need to be known. Should be filled
    once known!
    """
    __tablename__ = "ebd_stations"
    # Every station can only appear once!
    __table_args__ = (UniqueConstraint("network", "station"), {})
    id = Column(Integer, primary_key=True)
    network = Column(String, nullable=False, index=True)
    station = Column(String, nullable=False, index=True)
    latitude = Column(Float, nullable=True, index=True)
    longitude = Column(Float, nullable=True, index=True)
    elevation_in_m = Column(Float, nullable=True, index=True)
    local_depth_in_m = Column(Float, nullable=True, index=True)


class FilepathObject(Base):
    """
    Table containing all physical files stored on the disk.
    """
    __tablename__ = "ebd_filepaths"

    id = Column(Integer, primary_key=True)
    filepath = Column(String, nullable=False, unique=True)
    size = Column(Integer, nullable=False)
    mtime = Column(DateTime, nullable=False)
    md5_hash = Column(String, nullable=False)
    # This flag determines whether or not the file is managed by SeisHub. If it
    # is managed by SeisHub, SeisHub has the right to move, rename, and delete
    # the file. Otherwise it will never touch the file.
    is_managed_by_seishub = Column(Boolean, nullable=False)
    # An XML file containing information about the origin of the file.
    file_origin_resource_id = Column(Integer, nullable=True)


class ChannelMetadataObject(Base):
    """
    Table storing information about the channels. Every continuous interval
    will have a seperate entry even if they reside in the same file.
    """
    __tablename__ = "ebd_channel_metadata"
    # Every channel can only appear once
    __table_args__ = (UniqueConstraint("channel_id", "filepath_id",
        "starttime", "endtime"), {})

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey("ebd_channels.id"))
    filepath_id = Column(Integer, ForeignKey("ebd_filepaths.id"))
    starttime = Column(DateTime, nullable=False)
    endtime = Column(DateTime, nullable=True)
    format = Column(String, nullable=False)

    # Add relationsships to enable two way bindings.
    channel = relationship("ChannelObject",
        backref=backref("channel_metadata", order_by=id))
    filepath = relationship("FilepathObject",
        backref=backref("channel_metadata", order_by=id))


class WaveformChannelObject(Base):
    """
    Table containing information about every continuous waveform trace. Every
    trace will have its separate entry, even if they reside in the same file.
    """
    __tablename__ = "ebd_waveform_channels"

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey("ebd_channels.id"), nullable=False)
    filepath_id = Column(Integer, ForeignKey("ebd_filepaths.id"),
        nullable=False)
    # Link it to an actual resource.
    event_resource_id = Column(Integer, nullable=False)
    starttime = Column(DateTime, nullable=False)
    endtime = Column(DateTime, nullable=False)
    sampling_rate = Column(Float, nullable=False)
    format = Column(String, nullable=False)
    is_synthetic = Column(Boolean, nullable=False)
    # The metadata can be any XML document stored in the database.
    metadata_resource_id = Column(Integer, nullable=True)
    # Information about previous processing of the channel.
    processing_history_resource_id = Column(Integer, nullable=True)

    # Add relationsships to enable two way bindings.
    channel = relationship("ChannelObject",
        backref=backref("waveform_channel", order_by=id))
    filepath = relationship("FilepathObject",
        backref=backref("waveform_channel", order_by=id))
