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
import os
import unittest

from seishub.plugins.event_based_data.tests.test_case import \
    EventBasedDataTestCase


class EventTestCase(EventBasedDataTestCase):
    """
    Test case for the event resource.
    """
    def test_UploadingUnnamedEvent(self):
        """
        Tests the uploading via POST of a station RESP file. This is a rather
        extensive test case and test all steps.
        """
        event_file = os.path.join(self.data_dir, "event1.xml")
        with open(event_file, "rt") as open_file:
            org_data = self._strip_xml_declaration(unicode(open_file.read()))
        self._send_request("POST", "/xml/event_based_data/event", event_file)
        keys, results = self._query_for_complete_table(
            "/event_based_data/event")
        result = results[0]
        doc_id = result[keys.index("document_id")]
        doc = self._get_document(doc_id)
        self.assertEqual(doc, org_data)



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(EventTestCase, "test"))
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")
