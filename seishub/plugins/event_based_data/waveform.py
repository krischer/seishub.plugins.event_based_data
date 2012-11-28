#!/usr/bin/env python
# -*- coding: utf-8 -*-
from seishub.core.core import Component, implements
from seishub.core.exceptions import SeisHubError
from seishub.core.packages.interfaces import IMapper

import hashlib
from obspy.core import read
from twisted.web import http


class WaveformUploader(Component):
    """
    Upload waveform data.
    """
    implements(IMapper)

    package_id = "event_based_data"
    version = "0.0.0."
    mapping_url = "/event_based_data/waveform/upload"

    def process_GET(self, request):
        """
        Function that will be called upon receiving a GET request for the
        aforementioned URL.
        """
        # Get not allowed for this mapper. Return 404.
        raise SeisHubError("GET not supported for this URL.", http.NOT_FOUND)

    def process_POST(self, request):
        """
        Function that will be called upon receiving a GET request for the
        aforementioned URL.
        """
        request.content.seek(0,0)
        msg = ("The attached content does not appear to be a valid waveform "
               "file. Only data readable by ObsPy is acceptable.")
        # Only valid waveforms files will be stored in the database. Valid is
        # defined by being readable by ObsPy.
        try:
            st = read(request.content)
        except:
            raise SeisHubError(msg, code=http.NOT_ACCEPTABLE)

        # Read the data, calculate the md5 hash and check if the file already
        # exists.
        request.content.seek(0, 0)
        data = request.contest.read()
        md5_hash = hashlib.md5(data).hexdigest()



