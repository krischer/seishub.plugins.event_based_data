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
import os
import unittest

from seishub.core.exceptions import InvalidParameterError

from seishub.plugins.event_based_data.tests.test_case import \
    EventBasedDataTestCase
from seishub.plugins.event_based_data.table_definitions import FilepathObject,\
    StationObject, ChannelObject, ChannelMetadataObject


class WaveformTestCase(EventBasedDataTestCase):

    def test_uploadingWithoutSpecifyingAnEventFails(self):
        """
        Waveforms are always bound to an event. Uploading without one fails.
        """
        waveform_file = os.path.join(self.data_dir, "dis.PFVI..BHE")

        # Uploading without specifying an event fails.
        self.assertRaises(InvalidParameterError, self._send_request, "POST",
            waveform_file, "/event_based_data/waveform")


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(WaveformTestCase, "test"))
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")
