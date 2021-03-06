#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A test suite for waveform uploading.

:copyright:
    Lion Krischer (krischer@geophysik.uni-muenchen.de), 2012
:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html)
"""
import datetime
import json
from obspy import read
import os
from StringIO import StringIO
import unittest

from seishub.core.exceptions import InvalidParameterError, InvalidObjectError

from seishub.plugins.event_based_data.tests.test_case import \
    EventBasedDataTestCase
from seishub.plugins.event_based_data.table_definitions import FilepathObject,\
    StationObject, ChannelObject, WaveformChannelObject
from seishub.plugins.event_based_data.util import get_all_tags


class WaveformTestCase(EventBasedDataTestCase):
    """
    Test case for the waveform resource.
    """
    def test_uploadingWithoutSpecifyingAnEventFails(self):
        """
        Waveforms are always bound to an event. Uploading without one fails.
        """
        waveform_file = os.path.join(self.data_dir, "dis.PFVI..BHE")

        # Uploading without specifying an event fails.
        self.assertRaises(InvalidParameterError, self._send_request, "POST",
            "/event_based_data/waveform", waveform_file)

    def test_unknownEventIdRaises(self):
        """
        Uploading while referring to an unknown event id raises.
        """
        # Upload an event to be able to refer to one.
        self._upload_event()
        waveform_file = os.path.join(self.data_dir, "dis.PFVI..BHE")
        self.assertRaises(InvalidParameterError, self._send_request, "POST",
            "/event_based_data/waveform", waveform_file,
            {"event": "unknown_event"})

    def test_uploadingSingleSACFile(self):
        """
        Extensive test for a uploading a single sac file.
        """
        # Upload an event to be able to refer to one.
        self._upload_event()
        waveform_file = os.path.join(self.data_dir, "dis.PFVI..BHE")
        self._send_request("POST", "/event_based_data/waveform", waveform_file,
            {"event": "example_event"})
        with open(waveform_file, "rb") as open_file:
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
        # SAC files do contain coordinates.
        self.assertAlmostEqual(station.latitude, 37.132832, 5)
        self.assertAlmostEqual(station.longitude, -8.826829, 5)
        self.assertAlmostEqual(station.elevation_in_m, 189.0, 5)
        self.assertAlmostEqual(station.local_depth_in_m, 3.0, 5)
        # Assert the channel information.
        self.assertEqual(channel.location, "")
        self.assertEqual(channel.channel, "BHE")
        self.assertTrue(channel.station is station)

        # Check the waveform channel
        waveform = session.query(WaveformChannelObject).one()
        self.assertEqual(waveform.starttime,
            datetime.datetime(2012, 8, 27, 4, 43, 56, 35004))
        self.assertEqual(waveform.endtime,
            datetime.datetime(2012, 8, 27, 5, 48, 55, 985004))
        self.assertAlmostEqual(waveform.sampling_rate, 20.0)
        self.assertEqual(waveform.format, "SAC")
        self.assertEqual(waveform.is_synthetic, False)
        # Currently has no associate metadata and processing information
        self.assertEqual(waveform.metadata_resource_id, None)
        self.assertEqual(waveform.processing_history_resource_id, None)
        # Check the relationships.
        self.assertTrue(waveform.filepath is filepath_object)
        self.assertTrue(waveform.channel is channel)

        # Also check that it has been uploaded to the correct directory.
        self.assertEqual(os.listdir(os.path.join(self.tempdir, "waveform_data",
            "example_event")), ["PM.PFVI..BHE-2012_8_27_4"])

    def test_settingSyntheticsFlagMarksFileAsSynthetic(self):
        """
        Simple test that checks that a file uploaded with synthetic=true marks
        the file as a synthetic file.
        """
        # Upload an event to be able to refer to one.
        self._upload_event()

        # Set synthetic to true.
        waveform_file = os.path.join(self.data_dir, "dis.PFVI..BHE")
        self._send_request("POST",
            "/event_based_data/waveform", waveform_file,
            {"event": "example_event", "synthetic": "true"})
        session = self.env.db.session(bind=self.env.db.engine)
        waveform = session.query(WaveformChannelObject).one()
        self.assertEqual(waveform.is_synthetic, True)

    def test_settingSyntheticsFlagToFalseMarksFileAsNotSynthetic(self):
        """
        Simple test that checks that a file uploaded with synthetic=false marks
        the file as a non-synthetic file.
        """
        # Upload an event to be able to refer to one.
        self._upload_event()

        # Set synthetic to true.
        waveform_file = os.path.join(self.data_dir, "dis.PFVI..BHE")
        self._send_request("POST",
            "/event_based_data/waveform", waveform_file,
            {"event": "example_event", "synthetic": "false"})
        session = self.env.db.session(bind=self.env.db.engine)
        waveform = session.query(WaveformChannelObject).one()
        self.assertEqual(waveform.is_synthetic, False)

    def test_uploadingNonWaveformFileRaises(self):
        """
        Uploading a non-waveform file should raise an InvalidObjectError.
        """
        # Upload an event to be able to refer to one.
        self._upload_event()

        # Event file is not a waveform file.
        event_file = os.path.join(self.data_dir, "event1.xml")
        self.assertRaises(InvalidObjectError, self._send_request, "POST",
            "/event_based_data/waveform", event_file,
            {"event": "example_event"})

    def test_indexingNonExistantFileFailes(self):
        """
        Attempting to upload a non existent file fails.
        """
        # Upload an event to be able to refer to one.
        self._upload_event()

        random_file_url = "/bla/blu/blub.mseed"

        self.assertRaises(InvalidParameterError, self._send_request, "POST",
            "/event_based_data/waveform", None,
            {"event": "example_event", "index_file": random_file_url})

    def test_attemptingToUploadAFolderFails(self):
        """
        Attempting to upload a folder fails.
        """
        # Upload an event to be able to refer to one.
        self._upload_event()

        self.assertRaises(InvalidParameterError, self._send_request, "POST",
            "/event_based_data/waveform", None,
            {"event": "example_event", "index_file": self.data_dir})

    def test_indexWaveformFile(self):
        """
        Index a waveform file. Most things should be exactly the same as for
        the normal upload case. Only the file should of course not be copied.

        This test is almost identical to test_uploadingSingleSACFile().
        """
        # Upload an event to be able to refer to one.
        self._upload_event()
        waveform_file = os.path.join(self.data_dir, "dis.PFVI..BHE")
        self._send_request("POST", "/event_based_data/waveform", None,
            {"event": "example_event", "index_file": waveform_file})

        # Get the filepath object. Database should only contain one!
        session = self.env.db.session(bind=self.env.db.engine)
        filepath_object = session.query(FilepathObject).one()

        # The file is not managed by SeisHub.
        self.assertEqual(filepath_object.is_managed_by_seishub, False)
        # has no associated origin file.
        self.assertEqual(filepath_object.file_origin_resource_id, None)
        # The filepath should be identical to the actual file in this case.
        self.assertEqual(filepath_object.filepath,
            os.path.abspath(waveform_file))
        # The size should be identical to the stored size.
        self.assertEqual(filepath_object.size, os.path.getsize(waveform_file))

        # Now check the databases. Should contain exactly one entry in the
        # station table, one in the channels table and one in the metadata
        # table.
        station = session.query(StationObject).one()
        channel = session.query(ChannelObject).one()
        # Assert the station information
        self.assertEqual(station.network, "PM")
        self.assertEqual(station.station, "PFVI")
        # SAC files do contain coordinates.
        self.assertAlmostEqual(station.latitude, 37.132832, 5)
        self.assertAlmostEqual(station.longitude, -8.826829, 5)
        self.assertAlmostEqual(station.elevation_in_m, 189.0, 5)
        self.assertAlmostEqual(station.local_depth_in_m, 3.0, 5)
        # Assert the channel information.
        self.assertEqual(channel.location, "")
        self.assertEqual(channel.channel, "BHE")
        self.assertTrue(channel.station is station)

        # Check the waveform channel
        waveform = session.query(WaveformChannelObject).one()
        self.assertEqual(waveform.starttime,
            datetime.datetime(2012, 8, 27, 4, 43, 56, 35004))
        self.assertEqual(waveform.endtime,
            datetime.datetime(2012, 8, 27, 5, 48, 55, 985004))
        self.assertAlmostEqual(waveform.sampling_rate, 20.0)
        self.assertEqual(waveform.format, "SAC")
        self.assertEqual(waveform.is_synthetic, False)
        # Currently has no associate metadata and processing information
        self.assertEqual(waveform.metadata_resource_id, None)
        self.assertEqual(waveform.processing_history_resource_id, None)
        # Check the relationships.
        self.assertTrue(waveform.filepath is filepath_object)
        self.assertTrue(waveform.channel is channel)

        # Also check that the actual data directory has no entries!
        self.assertEqual(os.listdir(self.tempdir), [])

    def test_settingTags(self):
        """
        Tests if setting the tags works.
        """
        # Upload an event to be able to refer to one.
        self._upload_event()

        waveform_file = os.path.join(self.data_dir, "dis.PFVI..BHE")
        self._send_request("POST",
            "/event_based_data/waveform", waveform_file,
            {"event": "example_event", "tag": "some_tag"})
        session = self.env.db.session(bind=self.env.db.engine)
        waveform = session.query(WaveformChannelObject).one()
        self.assertEqual(waveform.tag, "some_tag")

        # Uploading the same tag again should fail. This time, slightly modify
        # the file as otherwise it will not be accepted anyways.
        waveform_file = os.path.join(self.data_dir, "dis.PFVI..BHE")
        st = read(waveform_file)
        st[0].stats.starttime += 2
        w_file = StringIO()
        st.write(w_file, format="mseed")
        w_file.seek(0, 0)
        self.assertRaises(InvalidParameterError, self._send_request, "POST",
            "/event_based_data/waveform", w_file,
            {"event": "example_event", "tag": "some_tag"})

        # Uploading the same file with another tag on the other hand should
        # work just fine.
        w_file.seek(0, 0)
        self._send_request("POST",
            "/event_based_data/waveform", w_file,
            {"event": "example_event", "tag": "some_other_tag"})

        # Now there should be two registered tags.
        s = st[0].stats
        tags = get_all_tags(s.network, s.station, s.location, s.channel,
            "example_event", self.env)
        self.assertEqual(tags, ["some_tag", "some_other_tag"])

    def test_emptyTag(self):
        """
        Setting an empty tag only works once. Then it raises.
        """
        # Upload an event to be able to refer to one.
        self._upload_event()

        waveform_file = os.path.join(self.data_dir, "dis.PFVI..BHE")
        self._send_request("POST",
            "/event_based_data/waveform", waveform_file,
            {"event": "example_event"})
        session = self.env.db.session(bind=self.env.db.engine)
        waveform = session.query(WaveformChannelObject).one()
        self.assertEqual(waveform.tag, "")

        # Uploading the same tag again should fail. This time, slightly modify
        # the file as otherwise it will not be accepted anyways.
        waveform_file = os.path.join(self.data_dir, "dis.PFVI..BHE")
        st = read(waveform_file)
        st[0].stats.starttime += 2
        w_file = StringIO()
        st.write(w_file, format="mseed")
        w_file.seek(0, 0)
        self.assertRaises(InvalidParameterError, self._send_request, "POST",
            "/event_based_data/waveform", w_file,
            {"event": "example_event"})

        # The empty tag still counts as a tag
        s = st[0].stats
        tags = get_all_tags(s.network, s.station, s.location, s.channel,
            "example_event", self.env)
        self.assertEqual(tags, [""])

    def test_getListOfWavformsForOneEvent(self):
        """
        Tests getting a list of all waveforms for one event.
        """
        # Upload an event to be able to refer to one.
        self._upload_event()

        # Upload some data.
        waveform_file = os.path.join(self.data_dir, "dis.PFVI..BHE")
        self._send_request("POST",
            "/event_based_data/waveform", waveform_file,
            {"event": "example_event"})
        session = self.env.db.session(bind=self.env.db.engine)
        waveform = session.query(WaveformChannelObject).one()
        self.assertEqual(waveform.tag, "")

        # Uploading the same tag again should fail. This time, slightly modify
        # the file as otherwise it will not be accepted anyways.
        waveform_file = os.path.join(self.data_dir, "dis.PFVI..BHE")
        st = read(waveform_file)
        st[0].stats.starttime += 2
        w_file = StringIO()
        st.write(w_file, format="mseed")
        w_file.seek(0, 0)
        self._send_request("POST",
            "/event_based_data/waveform", w_file,
            {"event": "example_event", "tag": "modified", "synthetic": "true"})

        # Now get a list of all waveforms for the specified event.
        response = self._send_request("GET", "/event_based_data/waveform",
            args={"event": "example_event", "format": "json"})
        response = json.loads(response)["ResultSet"]["Result"]

        # Assert them. Sort them by tags.
        response.sort(key=lambda x: x["tag"])
        self.assertEqual(len(response), 2)
        response1 = response[0]
        response2 = response[1]

        self.assertEqual({"channel": "BHE",
            "endtime": "2012-08-27T05:48:55.985004",
            "filepath_id": 1,
            "format": "SAC",
            "is_synthetic": False,
            "location": "",
            "network": "PM",
            "sampling_rate": 20.0,
            "starttime": "2012-08-27T04:43:56.035004",
            "station": "PFVI",
            "tag": ""}, response1)

        self.assertEqual({"channel": "BHE",
            "endtime": "2012-08-27T05:48:57.985003",
            "filepath_id": 2,
            "format": "MSEED",
            "is_synthetic": True,
            "location": "",
            "network": "PM",
            "sampling_rate": 20.0,
            "starttime": "2012-08-27T04:43:58.035003",
            "station": "PFVI",
            "tag": "modified"}, response2)

    def test_getWaveformFile(self):
        """
        Tests downloading a waveform file.
        """
        # Upload an event to be able to refer to one.
        self._upload_event()

        # Upload some data.
        waveform_file = os.path.join(self.data_dir, "dis.PFVI..BHE")
        self._send_request("POST",
            "/event_based_data/waveform", waveform_file,
            {"event": "example_event"})

        # Upload another file and slightly modify it.
        st = read(waveform_file)
        st[0].stats.starttime += 2
        st[0].data *= 1.5
        w_file = StringIO()
        st.write(w_file, format="mseed")
        w_file.seek(0, 0)
        self._send_request("POST",
            "/event_based_data/waveform", w_file,
            {"event": "example_event", "tag": "modified"})

        # Now download the first file again.
        data = self._send_request("GET",
            "/event_based_data/waveform", waveform_file,
            {"event": "example_event", "channel_id": "PM.PFVI..BHE"})
        old_st = read(waveform_file)
        new_st = read(StringIO(data))
        self.assertEqual(new_st, old_st)

        # And the second one.
        data = self._send_request("GET",
            "/event_based_data/waveform", waveform_file,
            {"event": "example_event", "channel_id": "PM.PFVI..BHE",
                "tag": "modified"})
        new_st = read(StringIO(data))

        # Remove the file format specific parts.
        del st[0].stats.sac
        del new_st[0].stats.mseed
        del st[0].stats._format
        del new_st[0].stats._format
        # Fix slightly inaccurate SAC starttime.
        self.assertTrue(
            abs(st[0].stats.starttime - new_st[0].stats.starttime) < 0.01)
        self.assertTrue(
            abs(st[0].stats.endtime - new_st[0].stats.endtime) < 0.01)
        st[0].stats.starttime = new_st[0].stats.starttime

        self.assertEqual(new_st, st)

    def test_downloadDifferentFormats(self):
        # Upload an event to be able to refer to one.
        self._upload_event()

        # Upload some data.
        waveform_file = os.path.join(self.data_dir, "dis.PFVI..BHE")
        self._send_request("POST",
            "/event_based_data/waveform", waveform_file,
            {"event": "example_event"})

        # Now download the first file again.
        data = self._send_request("GET",
            "/event_based_data/waveform", waveform_file,
            {"event": "example_event", "channel_id": "PM.PFVI..BHE"})
        old_st = read(waveform_file)
        new_st = read(StringIO(data))
        self.assertEqual(new_st, old_st)

        # Download MiniSEED data.
        data = self._send_request("GET",
            "/event_based_data/waveform", waveform_file,
            {"event": "example_event", "channel_id": "PM.PFVI..BHE",
            "format": "mseed"})
        st = read(StringIO(data))
        self.assertEqual(st[0].stats._format, "MSEED")

        # Remove the file format specific parts.
        del st[0].stats.mseed
        del old_st[0].stats.sac
        del st[0].stats._format
        del old_st[0].stats._format
        # Fix slightly inaccurate SAC starttime.
        self.assertTrue(
            abs(st[0].stats.starttime - old_st[0].stats.starttime) < 0.01)
        self.assertTrue(
            abs(st[0].stats.endtime - old_st[0].stats.endtime) < 0.01)
        st[0].stats.starttime = old_st[0].stats.starttime
        self.assertEqual(st, old_st)

        # Download SAC data.
        data = self._send_request("GET",
            "/event_based_data/waveform", waveform_file,
            {"event": "example_event", "channel_id": "PM.PFVI..BHE",
            "format": "sac"})
        st = read(StringIO(data))
        self.assertEqual(st[0].stats._format, "SAC")
        # Remove the file format specific parts.
        del st[0].stats.sac
        del st[0].stats._format
        self.assertEqual(st, old_st)

        # Download raw data. Should be byte for byte the same as the original
        # input data.
        data = self._send_request("GET",
            "/event_based_data/waveform", waveform_file,
            {"event": "example_event", "channel_id": "PM.PFVI..BHE",
            "format": "raw"})
        with open(waveform_file, "rb") as open_file:
            old_data = open_file.read()
        self.assertEqual(data, old_data)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(WaveformTestCase, "test"))
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")
