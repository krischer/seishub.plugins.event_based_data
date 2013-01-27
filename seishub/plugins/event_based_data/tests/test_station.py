#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A test suite for station resources.

:copyright:
    Lion Krischer (krischer@geophysik.uni-muenchen.de), 2012
:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html)
"""
import datetime
import inspect
import json
from obspy import UTCDateTime
import os
import StringIO
import unittest

from seishub.core.exceptions import InvalidObjectError, DuplicateObjectError, \
    InvalidParameterError

from seishub.plugins.event_based_data import station_mappers
from seishub.plugins.event_based_data.tests.test_case import \
    EventBasedDataTestCase
from seishub.plugins.event_based_data.table_definitions import FilepathObject,\
    StationObject, ChannelObject, ChannelMetadataObject


class StationTestCase(EventBasedDataTestCase):
    """
    Test case for the station resource.
    """
    def test_RESPFileUploading(self):
        """
        Tests the uploading via POST of a station RESP file. This is a rather
        extensive test case and test all steps.
        """
        resp_file = os.path.join(self.data_dir, "RESP.PM.PFVI..BHZ")
        self._send_request("POST", "/event_based_data/station",
            resp_file)
        with open(resp_file, "r") as open_file:
            data = open_file.read()

        # Get the filepath object. Database should only contain one!
        session = self.env.db.session(bind=self.env.db.engine)
        filepath_object = session.query(FilepathObject).one()

        # Check that the filepath stored in the database contains a file that
        # is identical to the input file.
        with open(filepath_object.filepath, "r") as open_file:
            actually_stored_file = open_file.read()
        self.assertEqual(data, actually_stored_file)
        # The filepath in this case is also managed by SeisHub.
        self.assertEqual(filepath_object.is_managed_by_seishub, True)
        # has no associated origin file.
        self.assertEqual(filepath_object.file_origin_resource_id, None)

        # Now check the databases. Should contain exactly one entry in the
        # station table, one in the channels table and one in the metadata
        # table.
        station = session.query(StationObject).one()
        channel = session.query(ChannelObject).one()
        # Assert the station information
        self.assertEqual(station.network, "PM")
        self.assertEqual(station.station, "PFVI")
        # RESP files do not contain coordinates.
        self.assertEqual(station.latitude, None)
        self.assertEqual(station.longitude, None)
        self.assertEqual(station.elevation_in_m, None)
        self.assertEqual(station.local_depth_in_m, None)
        # Assert the channel information.
        self.assertEqual(channel.location, "")
        self.assertEqual(channel.channel, "BHZ")
        self.assertTrue(channel.station is station)

        # Check the channel_metadata
        metadata = session.query(ChannelMetadataObject).one()
        self.assertEqual(metadata.starttime, datetime.datetime(2007, 1, 1))
        self.assertEqual(metadata.endtime, None)
        self.assertEqual(metadata.format, "RESP")
        # Check the relationships.
        self.assertTrue(metadata.filepath is filepath_object)
        self.assertTrue(metadata.channel is channel)

        # Also check that it has been uploaded to the correct directory.
        self.assertEqual(os.listdir(os.path.join(self.tempdir, "station_data",
            "PM")), ["PM.PFVI..BHZ-2007_1"])

    def test_getStationList(self):
        """
        Tests the retrieval of a list of all stations after uploading.
        """
        # Upload two files.
        resp_file = os.path.join(self.data_dir, "RESP.PM.PFVI..BHZ")
        self._send_request("POST", "/event_based_data/station", resp_file)
        xseed_file = os.path.join(self.data_dir, "dataless.seed.GR_GEC2.xml")
        self._send_request("POST", "/event_based_data/station", xseed_file)

        # Get a list of all
        response = self._send_request("GET", "/event_based_data/station",
            args={"format": "json"})

        response = json.loads(response)["ResultSet"]["Result"]
        response = sorted(response, key=lambda x: x["network"])
        self.assertEqual(len(response), 2)

        # Assert the first station
        self.assertEqual(response[0]["network"], "GR")
        self.assertEqual(response[0]["station"], "GEC2")
        channels = sorted([_i["channel"] for _i in response[0]["channels"]])
        self.assertEqual(channels, ["HHE", "HHN", "HHZ"])
        self.assertAlmostEqual(response[0]["latitude"], 48.845085)
        self.assertAlmostEqual(response[0]["longitude"], 13.701584)
        self.assertAlmostEqual(response[0]["elevation_in_m"], 1132.5)
        self.assertAlmostEqual(response[0]["local_depth_in_m"], 0.0)

        # Assert the second station
        self.assertEqual(response[1]["network"], "PM")
        self.assertEqual(response[1]["station"], "PFVI")
        self.assertEqual(response[1]["channels"][0]["channel"], "BHZ")
        # RESP file do not have coordinates.
        self.assertEqual(response[1]["latitude"], None)
        self.assertEqual(response[1]["longitude"], None)
        self.assertEqual(response[1]["elevation_in_m"], None)
        self.assertEqual(response[1]["local_depth_in_m"], None)

    def test_getStationListSingleStation(self):
        """
        Tests the retrieval of a list of one station after uploading.
        """
        resp_file = os.path.join(self.data_dir, "RESP.PM.PFVI..BHZ")
        response = self._send_request("POST", "/event_based_data/station",
            resp_file)
        response = self._send_request("GET", "/event_based_data/station",
            args={"format": "json"})
        response = json.loads(response)["ResultSet"]["Result"]
        self.assertEqual(len(response), 1)
        response = response[0]
        # Assert the station
        self.assertEqual(response["network"], "PM")
        self.assertEqual(response["station"], "PFVI")
        self.assertEqual(response["channels"][0]["channel"], "BHZ")
        # RESP file do not have coordinates.
        self.assertEqual(response["latitude"], None)
        self.assertEqual(response["longitude"], None)
        self.assertEqual(response["elevation_in_m"], None)
        self.assertEqual(response["local_depth_in_m"], None)

    def test_XSEEDFileUploading(self):
        """
        Tests the uploading via POST of a XSEED RESP file. This is a rather
        extensive test case and test all steps.
        """
        xseed_file = os.path.join(self.data_dir, "dataless.seed.GR_GEC2.xml")
        self. _send_request("POST", "/event_based_data/station",
            xseed_file)
        with open(xseed_file, "r") as open_file:
            data = open_file.read()

        # Get the filepath object. Database should only contain one!
        session = self.env.db.session(bind=self.env.db.engine)
        filepath_object = session.query(FilepathObject).one()

        # Check that the filepath stored in the database contains a file that
        # is identical to the input file.
        with open(filepath_object.filepath, "rb") as open_file:
            actually_stored_file = open_file.read()
        self.assertEqual(data, actually_stored_file)
        # The filepath in this case is also managed by SeisHub.
        self.assertEqual(filepath_object.is_managed_by_seishub, True)
        # has no associated origin file.
        self.assertEqual(filepath_object.file_origin_resource_id, None)

        # Now check the databases. Should contain exactly one entry in the
        # station table, three in the channels table and three in the metadata
        # table.
        station = session.query(StationObject).one()
        channels = session.query(ChannelObject).all()
        self.assertEqual(len(channels), 3)
        # Assert the station information
        self.assertEqual(station.network, "GR")
        self.assertEqual(station.station, "GEC2")
        self.assertEqual(station.latitude, 48.845085)
        self.assertEqual(station.longitude, 13.701584)
        self.assertEqual(station.elevation_in_m, 1132.5)
        self.assertEqual(station.local_depth_in_m, 0.0)
        # Assert the channel information. Location + station should be the same
        # for all.
        for channel in channels:
            self.assertTrue(channel.station is station)
            self.assertEqual(channel.location, "")
        # Three different channels should be given.
        channel_names = ["HHE", "HHN", "HHZ"]
        for channel in channels:
            self.assertTrue(channel.channel in channel_names)
            channel_names.pop(channel_names.index(channel.channel))
        self.assertEqual(len(channel_names), 0)

        # Check the channel_metadata
        metadatas = session.query(ChannelMetadataObject).all()
        self.assertEqual(len(metadatas), 3)
        # The metadata should actually be identical for all, except the channel
        # id.
        for metadata in metadatas:
            self.assertEqual(metadata.starttime,
                datetime.datetime(2002, 8, 8, 12))
            self.assertEqual(metadata.endtime, None)
            self.assertEqual(metadata.format, "XSEED")
            # Check the relationships.
            self.assertTrue(metadata.filepath is filepath_object)

        # Check the channel references.
        channels_from_metadata = [_i.channel for _i in metadatas]
        self.assertEqual(sorted(channels), sorted(channels_from_metadata))

    def test_uploadingInvalidResourceFails(self):
        """
        Uploading an invalid station resource should raise.
        """
        data = StringIO.StringIO("asldjfklasdjfjdiojvbaeiogjqio34j5903jedio")
        # Uploading should raise a 409 code which in this case corresponds to
        # an InvalidObjectError.
        self.assertRaises(InvalidObjectError, self._send_request, "POST",
            "/event_based_data/station", data)

    def test_uploadingTheSameFileTwiceFails(self):
        """
        Uploading the same file twice should raise an error.
        """
        xseed_file = os.path.join(self.data_dir, "dataless.seed.GR_GEC2.xml")

        # Upload once.
        self._send_request("POST", "/event_based_data/station", xseed_file)
        # Once more should fail. Also code 409 but a different error.
        self.assertRaises(DuplicateObjectError, self._send_request, "POST",
            "/event_based_data/station", xseed_file)

    def test_RESPFileIndexing(self):
        """
        Index a station file. Most things should be exactly the same as for
        the normal upload case. Only the file should of course not be copied.

        This test is almost identical to test_RESPFileUploading().
        """
        resp_file = os.path.join(self.data_dir, "RESP.PM.PFVI..BHZ")
        self._send_request("POST", "/event_based_data/station", None,
            {"index_file": resp_file})

        # Get the filepath object. Database should only contain one!
        session = self.env.db.session(bind=self.env.db.engine)
        filepath_object = session.query(FilepathObject).one()

        # The filepath in this case is not managed by SeisHub.
        self.assertEqual(filepath_object.is_managed_by_seishub, False)
        # has no associated origin file.
        self.assertEqual(filepath_object.file_origin_resource_id, None)
        # The filepath should be identical to the actual file in this case.
        self.assertEqual(filepath_object.filepath,
            os.path.abspath(resp_file))
        # The size should be identical to the stored size.
        self.assertEqual(filepath_object.size, os.path.getsize(resp_file))

        # Now check the databases. Should contain exactly one entry in the
        # station table, one in the channels table and one in the metadata
        # table.
        station = session.query(StationObject).one()
        channel = session.query(ChannelObject).one()
        # Assert the station information
        self.assertEqual(station.network, "PM")
        self.assertEqual(station.station, "PFVI")
        # RESP files do not contain coordinates.
        self.assertEqual(station.latitude, None)
        self.assertEqual(station.longitude, None)
        self.assertEqual(station.elevation_in_m, None)
        self.assertEqual(station.local_depth_in_m, None)
        # Assert the channel information.
        self.assertEqual(channel.location, "")
        self.assertEqual(channel.channel, "BHZ")
        self.assertTrue(channel.station is station)

        # Check the channel_metadata
        metadata = session.query(ChannelMetadataObject).one()
        self.assertEqual(metadata.starttime, datetime.datetime(2007, 1, 1))
        self.assertEqual(metadata.endtime, None)
        self.assertEqual(metadata.format, "RESP")
        # Check the relationships.
        self.assertTrue(metadata.filepath is filepath_object)
        self.assertTrue(metadata.channel is channel)

        # Also check that the actual data directory has no entries!
        self.assertEqual(os.listdir(self.tempdir), [])

    def test_indexingNonExistantFileFailes(self):
        """
        Attempting to upload a non existent file fails.
        """
        random_file_url = "/bla/blu/blub.resp"

        self.assertRaises(InvalidParameterError, self._send_request, "POST",
            "/event_based_data/station", None, {"index_file": random_file_url})

    def test_attemptingToUploadAFolderFails(self):
        """
        Attempting to upload a folder fails.
        """
        self.assertRaises(InvalidParameterError, self._send_request, "POST",
            "/event_based_data/station", None, {"index_file": self.data_dir})


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
        channels = station_mappers._read_SEED(data)
        self.assertEqual(len(channels), 3)
        self.assertEqual(channels,
        [{"network": "GR", "end_date": "", "format": "XSEED",
            "elevation": 1132.5, "longitude": 13.701584,
            "instrument": "STS2", "station": "GEC2", "location": "",
            "latitude": 48.845085, "local_depth": 0,
            "start_date": UTCDateTime(2002, 8, 8, 12, 0), "channel": "HHE"},
        {"network": "GR", "end_date": "", "format": "XSEED",
            "elevation": 1132.5, "longitude": 13.701584,
            "instrument": "STS2", "station": "GEC2", "location": "",
            "latitude": 48.845085, "local_depth": 0,
            "start_date": UTCDateTime(2002, 8, 8, 12, 0), "channel": "HHN"},
        {"network": "GR", "end_date": "", "format": "XSEED",
            "elevation": 1132.5, "longitude": 13.701584,
            "instrument": "STS2", "station": "GEC2", "location": "",
            "latitude": 48.845085, "local_depth": 0,
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
        channels = station_mappers._read_RESP(data)
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels, [
            {"network": "PM", "station": "PFVI", "location": "",
                "channel": "BHZ", "start_date": UTCDateTime(2007, 1, 1),
                "end_date": None, "format": "RESP", "latitude": None,
                "longitude": None, "elevation": None, "local_depth": None}])

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
        channels = station_mappers._read_RESP(data)
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0], {"station": "TPAW", "longitude": None,
            "network": "IW", "end_date": UTCDateTime(2999, 12, 31, 23, 59, 59),
            "format": "RESP", "latitude": None, "elevation": None,
            "local_depth": None, "start_date": UTCDateTime(2004, 7, 1, 0, 0),
            "channel": "BHE", "location": ""})


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(StationUtilityFunctionsTestCase, "test"))
    suite.addTest(unittest.makeSuite(StationTestCase, "test"))
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")
