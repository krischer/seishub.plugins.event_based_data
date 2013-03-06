#!/usr/bin/env python
# -*- coding: utf-8 -*-
# flake8: noqa
# Make sure it can run it a non-graphical environment.
import matplotlib
matplotlib.use('Agg')

from package import *
from event_mappers import *
from station_mappers import *
from waveform_mappers import *
from generic_mappers import *
