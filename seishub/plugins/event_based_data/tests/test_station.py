#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A test suite for station uploading.

:copyright:
    Lion Krischer (krischer@geophysik.uni-muenchen.de), 2012
:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html)
"""
import inspect
from obspy import UTCDateTime
import os
import shutil
import StringIO
import tempfile
import unittest

from seishub.core.test import SeisHubEnvironmentTestCase
from seishub.plugins.event_based_data import package, station_information


class StationTestCase(SeisHubEnvironmentTestCase):
    def setUp(self):
        self.env.enableComponent(package.EventBasedDataPackage)
        self.env.enableComponent(
            station_information.StationInformationUploader)
        self.env.tree.update()
        # Create a temporary directory where things are stored.
        self.tempdir = tempfile.mkdtemp()
        # Directory with the data files.
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(
            inspect.getfile(inspect.currentframe()))), "data")

    def tearDown(self):
        self.env.registry.db_deletePackage("event_based_data")
        # Remove the temporary directory.
        shutil.rmtree(self.tempdir)


class StationUtilityFunctionsTestCase(unittest.TestCase):
    """
    Test case for function in the station handling part that do not need an
    active SeisHub environment.
    """
    def setUp(self):
        # Directory with the data files.
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(
            inspect.getfile(inspect.currentframe()))), "data")

    def test_readSEEDFunction(self):
        """
        Tests the _read_SEED() function. The function expects a StringIO.
        """
        xseed_file = os.path.join(self.data_dir, "dataless.seed.GR_GEC2.xml")
        with open(xseed_file, "r") as open_file:
            data = StringIO.StringIO(open_file.read())
        data.seek(0, 0)

        # Read the file extract a list of channel information.
        channels = station_information._read_SEED(data)
        self.assertEqual(len(channels), 3)
        self.assertEqual(channels,
        [{"network": "GR", "end_date": "", "format": "SEED",
            "elevation": 1132.5, "longitude": 13.701584,
            "instrument": "STS2", "station": "GEC2", "location": "",
            "latitude": 48.845085,
            "start_date": UTCDateTime(2002, 8, 8, 12, 0), "channel": "HHE"},
        {"network": "GR", "end_date": "", "format": "SEED",
            "elevation": 1132.5, "longitude": 13.701584,
            "instrument": "STS2", "station": "GEC2", "location": "",
            "latitude": 48.845085,
            "start_date": UTCDateTime(2002, 8, 8, 12, 0), "channel": "HHN"},
        {"network": "GR", "end_date": "", "format": "SEED",
            "elevation": 1132.5, "longitude": 13.701584,
            "instrument": "STS2", "station": "GEC2", "location": "",
            "latitude": 48.845085,
            "start_date": UTCDateTime(2002, 8, 8, 12, 0), "channel": "HHZ"}])

    def test_readRESPFunction(self):
        """
        Tests the _read_RESP() function. This function expects a StringIO as an
        input file.
        """
        resp_file = os.path.join(self.data_dir, "RESP.PM.PFVI..BHZ")
        with open(resp_file, "r") as open_file:
            data = StringIO.StringIO(open_file.read())
        data.seek(0, 0)

        # This file only contains information about one channel. Check it.
        channels = station_information._read_RESP(data)
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels, [
            {"network": "PM", "station": "PFVI", "location": "",
                "channel": "BHZ", "start_date": UTCDateTime(2007, 1, 1),
                "end_date": None, "format": "RESP", "latitude": None,
                "longitude": None, "elevation": None}])

    def test_multiple_identical_channels_in_RESP(self):
        """
        Some RESP files have identical versions of the same channel in one
        file. This is a faulty file. In this case, only one version of the
        channel is returned.
        """
        # The file contains the same channel time span twice. Only one should
        # be returned.
        resp_file = os.path.join(self.data_dir, "RESP.IW.TPAW..BHE")
        with open(resp_file, "r") as open_file:
            data = StringIO.StringIO(open_file.read())
        data.seek(0, 0)

        # This file only contains information about one channel. Check it.
        channels = station_information._read_RESP(data)
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0], {"station": "TPAW", "longitude": None,
            "network": "IW", "end_date": UTCDateTime(2999, 12, 31, 23, 59, 59),
            "format": "RESP", "latitude": None, "elevation": None,
            "start_date": UTCDateTime(2004, 7, 1, 0, 0), "channel": "BHE",
            "location": ""})


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(StationUtilityFunctionsTestCase, "test"))
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")
