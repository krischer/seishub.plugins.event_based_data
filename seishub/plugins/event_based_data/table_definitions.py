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
    PickleType, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relation
from obspy.core import Trace, UTCDateTime
import numpy as np
from sqlalchemy.schema import UniqueConstraint
import pickle


Base = declarative_base()


class ChannelsTable(Base):
    """
    Database table containing channel information. Lat/lng/depth are nullable
    because they do not necessarily need to be known. Should be filled once
    known!
    """
    __tablename__ = "ebd_channels"
    # Every channel can only appear once
    __table_args__ = (UniqueConstraint("network", "station", "location",
        "channel"), {})

    id = Column(Integer, primary_key=True)
    network = Column(String, nullable=False, index=True)
    station = Column(String, nullable=False, index=True)
    location = Column(String, nullable=False, index=True)
    channel = Column(String, nullable=False, index=True)
    latitude = Column(Float, nullable=True, index=True)
    longitude = Column(Float, nullable=True, index=True)
    depth_in_m = Column(Float, nullable=True, index=True)


class FilepathsTable(Base):
    """
    Table containing all physical files stored on the disk.
    """
    __tablename__ = "ebd_filepaths"

    id = Column(Integer, primary_key=True)
    filepath = Column(String, nullable=False, unique=True)
    size = Column(Integer, nullable=False)
    mtime = Column(DateTime, nullable=False)
    md5_hash = Column(String, nullable=False)


class InstrumentResponsesTable(Base):
    """
    Table storing information about the channels. Every continuous interval
    will have a seperate entry even if they reside in the same file.
    """
    __tablename__ = "ebd_instrument_responses"
    # Every channel can only appear once
    __table_args__ = (UniqueConstraint("channel_id", "filepath_id",
        "starttime", "endtime"), {})

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey("ebd_channels.id"), nullable=False)
    filepath_id = Column(Integer, ForeignKey("ebd_filepaths.id"),
        nullable=False)
    starttime = Column(DateTime, nullable=False)
    endtime = Column(DateTime, nullable=False)
    format = Column(String, nullable=False)


class WaveformChannelsTable(Base):
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
