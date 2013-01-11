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
from seishub.core.exceptions import InvalidParameterError, NotFoundError
from seishub.core.packages.interfaces import IMapper

from obspy.imaging.beachball import Beachball
from PIL import Image
from sqlalchemy import Table, sql
from StringIO import StringIO


class EventListMapper(Component):
    """
    Generates a list of available seismic events.
    """
    implements(IMapper)

    package_id = "event_based_data"
    version = "0.0.0."
    mapping_url = "/event_based_data/event/getList"

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


class BeachBallMapper(Component):
    """
    Takes the resource_name of an event and returns a beachball.

    SEISHUB_URL/event_based_data/event/getBeachball?event=8
    """
    implements(IMapper)

    package_id = "event_based_data"
    version = "0.0.0."
    mapping_url = "/event_based_data/event/getBeachball"

    def process_GET(self, request):
        """
        Function that will be called upon receiving a GET request for the
        aforementioned URL.
        """
        event = request.args0.get("event")
        width = request.args0.get("width", 150)
        width = int(width)
        facecolor = request.args0.get("color", "red")

        if not event:
            raise InvalidParameterError("'event' parameter missing.")

        # Directly access the database via an SQLView which is automatically
        # created for every resource type and filled with all indexed values.
        tab = Table("/event_based_data/event", request.env.db.metadata,
                    autoload=True)

        # Build up the query.
        query = sql.select([tab.c["Mrr"], tab.c["Mtt"], tab.c["Mpp"],
            tab.c["Mrt"], tab.c["Mrp"], tab.c["Mtp"]]).where(
            tab.c["resource_name"] == event)

        # Execute the query.
        result = request.env.db.query(query)
        if result is None:
            raise NotFoundError("Event %s not found in database" % event)

        result = result.fetchone()
        if result is None:
            raise NotFoundError("Event %s not found in database" % event)

        # generate correct header
        request.setHeader('content-type', 'image/png; charset=UTF-8')

        # Eventually resize it as the Beachball plotting method has
        # singularities for small image sizes.
        real_width = width if width >= 100 else 100
        data = StringIO(Beachball(result.values(), linewidth=3.5, format="png",
            width=real_width, facecolor=facecolor))
        if width < real_width:
            im = Image.open(data).resize((width, width), Image.ANTIALIAS)
            buf = StringIO()
            im.save(buf, format="png")
            buf.seek(0, 0)
            return buf.read()
        return data.read()
