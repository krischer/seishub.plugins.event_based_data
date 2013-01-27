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
from seishub.core.processor import GET, POST, Processor

import matplotlib.pyplot as plt
from obspy.imaging.beachball import Beachball
from sqlalchemy import Table, sql
from StringIO import StringIO


class EventMapper(Component):
    """
    Event mapper.
    """
    implements(IMapper)

    package_id = "event_based_data"
    version = "0.0.0."
    mapping_url = "/event_based_data/event"

    def process_GET(self, request):
        """
        Function that will be called upon receiving a GET request for the
        aforementioned URL.
        """
        # If a postpath is not given, return a list of all events.
        if not request.postpath:
            return self.get_event_list(request)
        # getBeachball will return a rendered beachball.
        if len(request.postpath) == 1 and \
            request.postpath[0].startswith("getBeachball"):
            return self.get_beachball(request)
        # Otherwise, just pass to the event xml resource handler.
        proc = Processor(self.env)
        return proc.run(GET, "/xml/event_based_data/event/" +
            "/".join(request.postpath), None)

    def process_POST(self, request):
        """
        Just remap to the xml rest interface.
        """
        # Otherwise, just pass to the event xml resource handler.
        proc = Processor(self.env)
        path = "/xml/event_based_data/event"
        if request.postpath:
            path += "/" + "/".join(request.postpath)
        return proc.run(POST, path, StringIO(request.data))

    def get_event_list(self, request):
        """
        Return a formatted list of events.
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

    def get_beachball(self, request):
        """
        Takes the resource_name of an event and returns a beachball.

        SEISHUB_URL/event_based_data/event/getBeachball?event=8
        """
        # Manual argument parsing is necessary. Unfortunately Seishub does not
        # have wildcard routes.
        # XXX: Check what happens with escaped HTML.
        arg_start = request.postpath[0].find("?")
        args = request.postpath[0][arg_start + 1:].split("&")
        args = {_i.split("=")[0]: _i.split("=")[1] for _i in args}
        # Somethings remain in the requests args as well.
        # XXX: Fix this in SeisHub!
        args.update(request.args)

        event = args.get("event")
        width = args.get("width", 150)
        width = int(width)
        facecolor = args.get("color", "red")

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

        # Setup the figure to get the desired file size.
        fig = plt.figure(figsize=(3, 3), dpi=100)
        fig.subplots_adjust(left=0, bottom=0, right=1, top=1)
        fig.set_figheight(width / 100.0)
        fig.set_figwidth(width / 100.0)

        image_data = Beachball(result.values(), linewidth=3.5, format="png",
            fig=fig, facecolor=facecolor)

        return image_data
