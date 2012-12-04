# -*- coding: utf-8 -*-
"""
Event-based data plug-in for SeisHub.
"""
from seishub.core.core import Component, implements
from seishub.core.config import Option
from seishub.core.packages.installer import registerIndex
from seishub.core.packages.interfaces import IPackage, IResourceType

import os

from table_definitions import Base


class EventBasedDataPackage(Component):
    """
    Event-based data package for SeisHub.
    """
    implements(IPackage)
    package_id = "event_based_data"
    version = "0.0.0"

    Option("event_based_data", "waveform_filepath", "",
        "Determines where the binary waveforms will be stored upon uploading.")
    Option("event_based_data", "station_filepath", "",
        ("Determines where the station information files will be stored upon "
        "uploading."))

    def __init__(self, *args, **kwargs):
        super(EventBasedDataPackage, self).__init__(*args, **kwargs)
        # Initialize all database tables. They will be created if they do not
        # exist yet.
        Base.metadata.create_all(self.env.db.engine, checkfirst=True)
        # Check if the data paths are set, if not assign default paths in the
        # SeisHub instance folder.
        if self.env.config.get("event_based_data", "waveform_filepath") == "":
            self.env.config.set("event_based_data", "waveform_filepath",
                os.path.join(self.env.getInstancePath(), "data", "waveforms"))
        if self.env.config.get("event_based_data", "station_filepath") == "":
            self.env.config.set("event_based_data", "station_filepath",
                os.path.join(self.env.getInstancePath(), "data", "responses"))
        # Save the config file to the values can written.
        self.env.config.save()
        # Make sure the paths exist.
        paths = [self.env.config.get("event_based_data", "waveform_filepath"),
            self.env.config.get("event_based_data", "station_filepath")]
        for path in paths:
            if not os.path.exists(path):
                os.makedirs(path)


class EventResourceType(Component):
    """
    A single event resource.
    """
    implements(IResourceType)

    # Specify the package name of the resource. The package also has to be
    # defined - in this case this is defined in the TemplateComponent class.
    package_id = "event_based_data"
    # The resource type name. Resources of this type will now be available
    # under SEISHUB_URL/xml/template/some_resource.
    resourcetype_id = "event"

    # Register some indices so the events can easily be searched.
    registerIndex("time", "/{http://quakeml.org/xmlns/quakeml/1.2}"
            "quakeml/eventParameters/event/origin/time/value", "datetime")
    registerIndex("latitude", "/{http://quakeml.org/xmlns/quakeml/1.2}"
            "quakeml/eventParameters/event/origin/latitude/value", "float")
    registerIndex("longitude", "/{http://quakeml.org/xmlns/quakeml/1.2}"
            "quakeml/eventParameters/event/origin/longitude/value", "float")
    registerIndex("depth", "/{http://quakeml.org/xmlns/quakeml/1.2}"
            "quakeml/eventParameters/event/origin/depth/value", "float")
    registerIndex("magnitude", "/{http://quakeml.org/xmlns/quakeml/1.2}"
            "quakeml/eventParameters/event/magnitude/mag/value", "float")
    registerIndex("magnitude_type", "/{http://quakeml.org/xmlns/quakeml/1.2}"
            "quakeml/eventParameters/event/magnitude/type", "text")
