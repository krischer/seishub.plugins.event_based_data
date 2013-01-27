# seishub.plugins.event_based_data

## Introduction

This plug-in aims to provide a mean to store event based waveform data and
associated station metadata. It is intended to handle the needs of everyone
dealing with large amounts of real and synthetic, event bound seismologcial
waveforms.  Waveforms are always bound to an earthquake (or potentially an
earthquake group) - the natural interpretation being that the waveform recorded
the earthquake.

Waveforms can be described in more detail with the help of three additional
pieces:

* **Station metadata** -> Sufficient to fully describe raw waveforms
* **Processing.xml** -> A (yet-to-be-defined) XML format detailing the (signal)
  processing that has been applied to the waveform.
* **Synthetic.xml** -> A (yet-to-be-defined) XML format detailing the origin of
  the waveform. This mostly means the solver used to generate the waveform, the
  mesh and model it operated on and other parameters.

The combined usage of these three resources and the event they are bound to
should be able to completely describe any waveform that occurs e.g. in the
course of a tomographic inversion.

## Installation

### Requirements

    * Python 2.7.x (should work with 2.6 but that is untested)
    * seishub.core
    * ObsPy >= 0.8.3
    * PIL (only for running the tests)

And naturally all dependencies of the listed modules.

### Normal installation

```bash
pip install .
``

or  (if you prefer it)

```bash
python setup.py install
```

### Develop installation
If you intend to change any of the source code files it should be installed in
develop mode. This means that the installation script will not copy all files
to your `site-packages` directory but just set a symlink. Therefore any changes
to the source will be applied.

```bash
pip install -v -e .
```

or  (if you prefer it)

```bash
python setup.py develop
```

### Activation

Start the Seishub server, go to `ADDRESS:PORT/manage` -> Plug-ins and activate
all components of it.

### Configuration
The plug-in has two plug-in specific configuration options (can be set in
`SEISHUB_ENV/conf/seishub.ini` after the plug-in has been activated):

* **waveform_filepath**: Determines where the binary waveforms will be stored
  upon uploading. Can become a significant amount of data.
* **station_filepath**: Determines where the station information files will be
  stored upon uploading.

Restart the Seishub server to apply the options.


# API Documentation

`BASE` always refers to the base SeisHub URL of the server including the port
number. Most data is bound to a certain event. In that case the event parameter
should be given in the form `event=EVENT_NAME` and appended to the url. This in
unified across all event bound data types.

## Event data

Most data is, as the plug-in name implies bound to a certain event. Thus
uploading a new event is always the first step. Currently only the QuakeML
format is accepted.

### Upload a new event

`POST BASE/event_based_data/event/EVENT_NAME`

The event will receive a numerical number if `EVENT_NAME` is not given.

### Retrieve an event

`GET BASE/event_based_data/event/EVENT_NAME`

### Get a list of all events

`GET BASE/event_based_data/event`

**Options:**
* `format`: Determines the format of the list.
    * `xml`: default
    * `json`
    * `xhtml`

### Get a Beachball plot of an event stored in the database

`GET BASE/event_based_data/event/getBeachball?event=EVENT_NAME`

**Options:**
    * `event`: The name of the event (required)
    * `width`: The width of the returned image (default: `150`)
    * `facecolor`: The color of the beachball (default: `'red'`)

Will return a png image.

## Station data

Station data is not bound to any event as it is potentially shared between many
events. Currently the following file formats are supported:

* SEED
* XML-SEED
* RESP (needs corresponding SAC files to get station coordinates)

### "RESTful" station interface

#### Upload a new station:
`POST BASE/event_based_data/station`

#### Get a list of all stations
`GET BASE/event_based_data/station`

#### Get the originally uploaded file of one specific station resource
`GET BASE/event_based_data/station?network=network_code&station=station_code`


### Waveform data

All waveform formats supported by ObsPy can be uploaded. Every waveform needs
to be bound to an already existing event

#### Upload a new waveform file:
`POST BASE/event_based_data/waveform?event=EVENT_NAME`

#### Get a list of all waveform for a given event
`GET BASE/event_based_data/waveform?event=EVENT_NAME`

#### Index (not upload) a new waveform file:

It is oftentimes desirable to just index data and not let it be managed by
SeisHub. Passing an absolute file path (that the server can see) to the
`index_file` parameter results results in the file being indexed and entered
into the database while the actual file stays where it is. In this case the
file is not managed by SeisHub, just indexed.

`POST BASE/event_based_data/waveform?event=EVENT_NAME&index_file=%2Ffile%2Fpath`
