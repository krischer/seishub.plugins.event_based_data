#!/usr/bin/env python
# -*- coding: utf-8 -*-
from seishub.core.core import Component, implements
from seishub.core.exceptions import NotFoundError, InternalServerError, \
    InvalidParameterError
from seishub.core.packages.interfaces import IMapper

import os

from table_definitions import FilepathObject


class FileDownloadMapper(Component):
    """
    Download a file with a given filepath id
    """
    implements(IMapper)

    package_id = "event_based_data"
    version = "0.0.0."
    mapping_url = "/event_based_data/downloadFile"

    def process_GET(self, request):
        filepath_id = request.args.get("filepath_id", [])
        if not filepath_id:
            msg = "File with the given id not found."
            raise InvalidParameterError(msg)
        filepath_id = int(filepath_id[0])
        session = self.env.db.session(bind=self.env.db.engine)
        query = session.query(FilepathObject)\
            .filter(FilepathObject.id == filepath_id).first()
        if not query:
            msg = "File with the given id not found."
            raise NotFoundError(msg)
        filename = query.filepath
        try:
            with open(filename, "rb") as open_file:
                data = open_file.read()
        except:
            msg = "Error reading data."
            raise InternalServerError(msg)

        # Set the corresponding headers.
        request.setHeader("content-type", "application/octet-stream")
        filename = os.path.basename(query.filepath).encode("utf-8")
        request.setHeader("content-disposition", "attachment; filename=%s" %
            filename)

        return data
