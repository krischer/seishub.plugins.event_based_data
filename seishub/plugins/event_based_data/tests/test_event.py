#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A test suite for event resources.

:copyright:
    Lion Krischer (krischer@geophysik.uni-muenchen.de), 2012
:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html)
"""
import json
import os
from PIL import Image
from StringIO import StringIO
import unittest

from seishub.plugins.event_based_data.tests.test_case import \
    EventBasedDataTestCase


class EventTestCase(EventBasedDataTestCase):
    """
    Test case for the event resource.
    """
    def test_UploadingUnnamedEventViaXML(self):
        """
        Tests the uploading of an unnamed event.
        """
        # Upload event.
        event_file = os.path.join(self.data_dir, "event1.xml")
        self._send_request("POST", "/xml/event_based_data/event", event_file)
        # Check if the uploaded data is correct!
        with open(event_file, "rt") as open_file:
            org_data = self._strip_xml_declaration(unicode(open_file.read()))
        keys, results = self._query_for_complete_table(
            "/event_based_data/event")
        result = results[0]
        doc_id = result[keys.index("document_id")]
        doc = self._get_document(doc_id)
        self.assertEqual(doc, org_data)

    def test_UploadingUnnamedEventViaMapper(self):
        """
        Same as test_UploadingUnnamedEventViaXML() but using the mapper.
        """
        # Upload event.
        event_file = os.path.join(self.data_dir, "event1.xml")
        self._send_request("POST", "/event_based_data/event", event_file)
        # Check if the uploaded data is correct!
        with open(event_file, "rt") as open_file:
            org_data = self._strip_xml_declaration(unicode(open_file.read()))
        keys, results = self._query_for_complete_table(
            "/event_based_data/event")
        result = results[0]
        doc_id = result[keys.index("document_id")]
        doc = self._get_document(doc_id)
        self.assertEqual(doc, org_data)

    def test_UploadingNamedEventViaXML(self):
        """
        Tests the uploading of a named event.
        """
        # Upload event.
        event_file = os.path.join(self.data_dir, "event1.xml")
        self._send_request("POST", "/xml/event_based_data/event/ABcDE",
            event_file)
        # Check if the uploaded data is correct!
        with open(event_file, "rt") as open_file:
            org_data = self._strip_xml_declaration(unicode(open_file.read()))
        keys, results = self._query_for_complete_table(
            "/event_based_data/event")
        result = results[0]
        doc_id = result[keys.index("document_id")]
        doc = self._get_document(doc_id)
        self.assertEqual(doc, org_data)
        # Check if the name is correct.
        res_name = doc_id = result[keys.index("resource_name")]
        self.assertEqual(res_name, "ABcDE")

    def test_UploadingNamedEventViaMapper(self):
        """
        Same as test_UploadingNamedEventViaXML() but via the mapper.
        """
        # Upload event.
        event_file = os.path.join(self.data_dir, "event1.xml")
        self._send_request("POST", "/event_based_data/event/ABcDE",
            event_file)
        # Check if the uploaded data is correct!
        with open(event_file, "rt") as open_file:
            org_data = self._strip_xml_declaration(unicode(open_file.read()))
        keys, results = self._query_for_complete_table(
            "/event_based_data/event")
        result = results[0]
        doc_id = result[keys.index("document_id")]
        doc = self._get_document(doc_id)
        self.assertEqual(doc, org_data)
        # Check if the name is correct.
        res_name = doc_id = result[keys.index("resource_name")]
        self.assertEqual(res_name, "ABcDE")

    def test_DownloadingEventViaXML(self):
        """
        Tests if the downloading of events works.
        """
        # Upload event.
        event_file = os.path.join(self.data_dir, "event1.xml")
        self._send_request("POST", "/xml/event_based_data/event/TEST_EVENT",
            event_file)
        data = self._send_request("GET",
            "/xml/event_based_data/event/TEST_EVENT", event_file)
        # Get original data.
        with open(event_file, "rt") as open_file:
            org_data = self._strip_xml_declaration(open_file.read())
        self.assertEqual(data, org_data)

    def test_DownloadingEventViaMapper(self):
        """
        Same as test_DownloadingEventViaXML() but via the mapper.
        """
        # Upload event.
        event_file = os.path.join(self.data_dir, "event1.xml")
        self._send_request("POST", "/xml/event_based_data/event/TEST_EVENT",
            event_file)
        data = self._send_request("GET",
            "/xml/event_based_data/event/TEST_EVENT", event_file)
        # Get original data.
        with open(event_file, "rt") as open_file:
            org_data = self._strip_xml_declaration(open_file.read())
        self.assertEqual(data, org_data)

    def test_GetEventList(self):
        """
        Tests if getting a list of all uploaded events works.
        """
        event_file_1 = os.path.join(self.data_dir, "event1.xml")
        self._send_request("POST", "/xml/event_based_data/event/TEST_EVENT_1",
            event_file_1)
        event_file_2 = os.path.join(self.data_dir, "event2.xml")
        self._send_request("POST", "/xml/event_based_data/event/TEST_EVENT_2",
            event_file_2)
        # Now get a list. Use json format as it is easy to pass. The other
        # formats are tested elsewhere.
        response = self._send_request("GET", "/event_based_data/event",
            args={"format": "json"})
        response = json.loads(response)[u"ResultSet"][u"Result"]
        # Do two very simple assertions. The rest is basically assured by
        # Seishubs xml handling.
        events = sorted([str(_i["resource_name"]) for _i in response])
        self.assertEqual(events, ["TEST_EVENT_1", "TEST_EVENT_2"])
        keys = [str(_i) for _i in sorted(response[0].keys())]
        self.assertEqual(keys, ['Mpp', 'Mrp', 'Mrr', 'Mrt', 'Mtp', 'Mtt',
            'depth', 'document_id', 'document_last_modified', 'latitude',
            'longitude', 'magnitude', 'magnitude_type', 'package_id',
            'resource_name', 'resourcetype_id', 'scalar_moment', 'time'])

    def test_getEventBeachball(self):
        """
        Tests the get beachball mapper.
        """
        # Upload event.
        event_file = os.path.join(self.data_dir, "event1.xml")
        self._send_request("POST", "/xml/event_based_data/event/TEST_EVENT",
            event_file)
        # Get the image.
        image = self._send_request("GET",
            "/event_based_data/event/getBeachball?event=TEST_EVENT",
            args={"width": 222})
        # Use pil to check the image.
        im = Image.open(StringIO(image))
        self.assertEqual(im.format, "PNG")
        self.assertEqual(im.size, (222, 222))
        self.assertEqual(im.mode, "RGBA")

    def test_getEventBeachballTestColorARg(self):
        """
        Tests the get beachball mapper. Simply assert that the color does
        something.
        """
        # Upload event.
        event_file = os.path.join(self.data_dir, "event1.xml")
        self._send_request("POST", "/xml/event_based_data/event/TEST_EVENT",
            event_file)
        # Get the image.
        image_1 = self._send_request("GET",
            "/event_based_data/event/getBeachball?event=TEST_EVENT",
            args={"color": "blue"})
        image_2 = self._send_request("GET",
            "/event_based_data/event/getBeachball?event=TEST_EVENT",
            args={"color": "yellow"})
        self.assertNotEqual(image_1, image_2)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(EventTestCase, "test"))
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")
