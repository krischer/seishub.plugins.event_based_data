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
from sqlalchemy import Table, sql
import StringIO
import tempfile

from seishub.core.test import SeisHubEnvironmentTestCase
from seishub.core.processor import Processor, GET, POST, PUT, DELETE

from seishub.plugins.event_based_data import package, waveform_mappers, \
    station_mappers, event_mappers


class EventBasedDataTestCase(SeisHubEnvironmentTestCase):
    def setUp(self):
        # Enable the package.
        self.env.enableComponent(package.EventBasedDataPackage)
        # Enable the XML resources
        self.env.enableComponent(package.EventResourceType)
        # Enable the mappers.
        self.env.enableComponent(station_mappers.StationMapper)
        self.env.enableComponent(event_mappers.EventMapper)
        self.env.enableComponent(waveform_mappers.WaveformMapper)
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
        # Delete the resource types.
        self.env.registry.db_deleteResourceType('event_based_data', 'event')
        # Delete the package.
        self.env.registry.db_deletePackage("event_based_data")
        # Remove the temporary directory.
        shutil.rmtree(self.tempdir)

    def _send_request(self, method, url, file_or_fileobject=None, args=None):
        """
        Uploads a file with the given method to the given url.

        :type method: string
        :param method: GET, POST, PUT, or DELETE
        :type url: string
        :param url: The url to upload to
        :type file_or_fileobject: string or file-like object
        :param file_or_fileobject: The file or file like object to upload. If
            None, then nothing will be uploaded.
        :type args: dictionary
        :param args: The arguments of the request. This is the same as any
        parameters appended to the URL.


        file_or_fileobject can be either a StringIO with some data or a
        filename.

        Returns the respone from the request.
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
        # Append potential arguments.
        if args:
            # Convert everything to strings. The processor usually deals with
            # URL where everything is a string by default.
            proc.args = {key: [str(value)] for (key, value) in
                args.iteritems()}
        if file_or_fileobject:
            if not hasattr(file_or_fileobject, "read") or \
                    not hasattr(file_or_fileobject, "seek"):
                with open(file_or_fileobject, "r") as open_file:
                    file_or_fileobject = StringIO.StringIO(open_file.read())
        else:
            file_or_fileobject = None
        response = proc.run(method, url, file_or_fileobject)
        if method == "GET" and hasattr(response, "render_GET"):

            class dummy(object):
                pass
            dum = dummy()
            dum.args = {}
            dum.env = dummy()
            dum.env.auth = dummy()
            temp = dummy()
            temp.permissions = 755
            dum.env.auth.getUser = lambda x: temp

            return self._strip_xml_declaration(response.render_GET(dum))
        return response

    def _query_for_complete_table(self, table):
        """
        Query the db for all contents of a table. Very useful for testing. Will
        return (None, None), if the table contains no entries.
        """
        tab = Table(table, self.env.db.metadata, autoload=True)
        # Build up the query.
        query = sql.select([tab])
        # Execute the query.
        result = self.env.db.query(query)
        if result:
            return result.keys(), result.fetchall()
        return (None, None)

    def _get_document(self, document_id):
        """
        Returns the document stored in the xml database with the given document
        id. Again useful for testing. Returns None, if not found.
        """
        tab = Table("default_document", self.env.db.metadata, autoload=True)
        # Build up the query.
        query = sql.select([tab.c["data"]]).where(tab.c["id"] == document_id)
        # Execute the query.
        result = self.env.db.query(query)
        if result:
            return result.fetchone()[0]
        else:
            return None

    def _strip_xml_declaration(self, document):
        """
        Removes an xml declaration like
            <?xml version='1.0' encoding='utf-8'?>
        from string and returns it.
        """
        idx = document.find("?>")
        if idx:
            return document[idx + 2:].strip()
        return document

    def _upload_event(self):
        """
        Waveform data has to be bound to an event. This convenience functions
        uploads a simple example event, named 'example_event'.
        """
        event_file = os.path.join(self.data_dir, "event1.xml")
        self._send_request("POST", "/xml/event_based_data/event/example_event",
            event_file)
