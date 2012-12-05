# -*- coding: utf-8 -*-
import unittest

# Import the necessary files and append them to a list. These modules will be
# searched for unittests.
import test_station
import test_waveform
modules = (test_station, test_waveform)


def suite():
    """
    Automatic unittest discovery.
    """
    suite = unittest.TestSuite()
    for module in modules:
        for attrib in dir(module):
            value = getattr(module, attrib)
            try:
                if issubclass(value, unittest.TestCase):
                    suite.addTest(unittest.makeSuite(value, "test"))
            except:
                pass
    return suite

if __name__ == "__main__":
    unittest.main(defaultTest="suite")
