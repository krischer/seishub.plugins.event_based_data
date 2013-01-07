#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Event mappers.

:copyright:
    Lion Krischer (krischer@geophysik.uni-muenchen.de), 2013
:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html)
"""
from seishub.core.core import Component, implements
from seishub.core.db.util import formatResults
from seishub.core.packages.interfaces import IMapper

import datetime
from sqlalchemy import Table, sql


class EventListMapper(Component):
    """
    Generates a list of available seismic events.
    """
    implements(IMapper)

    package_id = "event_based_data"
    version = "0.0.0."
    mapping_url = "/event_based_data/events/getList"

    def process_GET(self, request):
        """
        Function that will be called upon receiving a GET request for the
        aforementioned URL.
        """
        # Directly access the database via an SQLView which is automatically
        # created for every resource type and filled with all indexed values.
        tab = Table("/event_based_data/event", request.env.db.metadata,
                    autoload=True)

        # Build up the query.
        query = sql.select([tab])

        # Execute the query.
        result = request.env.db.query(query)

        # Use a convenience function provided by SeisHub to get a nicely
        # formatted output.
        result = formatResults(request, result)
        return result
