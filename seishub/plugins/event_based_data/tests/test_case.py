#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The test case class to make testing to facilitate the testing of the event
based data plugin.

:copyright:
    Lion Krischer (krischer@geophysik.uni-muenchen.de), 2012
:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html)
"""
import inspect
import os
import shutil
import StringIO
import tempfile

from seishub.core.test import SeisHubEnvironmentTestCase
from seishub.core.processor import Processor, GET, POST, PUT, DELETE

from seishub.plugins.event_based_data import package, waveform, \
    station_information


class EventBasedDataTestCase(SeisHubEnvironmentTestCase):
    def setUp(self):
        # Enable the package.
        self.env.enableComponent(package.EventBasedDataPackage)
        self.env.enableComponent(
        # Enable the components.
            station_information.StationInformationUploader)
        self.env.enableComponent(waveform.WaveformUploader)
        self.env.tree.update()
        # Create a temporary directory where things are stored.
        self.tempdir = tempfile.mkdtemp()
        # Set the filepaths for the plug-in to the temporary directory so all
        # files will be written there.
        self.env.config.set("event_based_data", "station_filepath",
            os.path.join(self.tempdir, "station_data"))
        self.env.config.set("event_based_data", "waveform_filepath",
            os.path.join(self.tempdir, "waveform_data"))

        # Directory with the data test files.
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(
            inspect.getfile(inspect.currentframe()))), "data")

    def tearDown(self):
        self.env.registry.db_deletePackage("event_based_data")
        # Remove the temporary directory.
        shutil.rmtree(self.tempdir)

    def _send_request(self, method, url, file_or_fileobject):
        """
        Uploads a file with the given method to the given url.

        :type method: str
        :param method: GET, POST, PUT, or DELETE
        :type url: str
        :param url: The url to upload to
        :type file_or_fileobject: str or None
        :param file_or_fileobject: The file or file like object to upload. If
            None, then nothing will be uploaded.

        file_or_fileobject can be either a StringIO with some data or a
        filename.

        Returns the data from the file as a StringIO with the pointer set to 0
        if a file has been read.
        """
        if method.upper() == "GET":
            method = GET
        elif method.upper() == "POST":
            method = POST
        elif method.upper() == "PUT":
            method = PUT
        elif method.upper() == "DELETE":
            method = DELETE
        else:
            msg = "Unknown method '%s'." % method
            raise ValueError(msg)

        proc = Processor(self.env)
        if file_or_fileobject:
            if not hasattr(file_or_fileobject, "read") or \
                not hasattr(file_or_fileobject, "seek"):
                with open(file_or_fileobject, "r") as open_file:
                    file_or_fileobject = StringIO.StringIO(open_file.read())
        else:
            file_or_fileobject = None
        proc.run(method, url, file_or_fileobject)
        if file_or_fileobject:
            file_or_fileobject.seek(0, 0)
            return file_or_fileobject.read()

    def _upload_event(self):
        """
        Waveform data has to be bound to an event. This convenience functions
        uploads a simple example event, named 'example_event'.
        """
        self._send_request("POST", os.path.join(self.data_dir,
            "example_event.xml"), "/xml/event_based_data/event/example_event")
