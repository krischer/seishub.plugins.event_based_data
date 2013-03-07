# seishub.plugins.event_based_data

## Introduction

This plug-in aims to provide a mean to store event based waveform data and
associated station metadata. It is intended to handle the needs of everyone
dealing with large amounts of real and synthetic, event bound seismologcial
waveforms.  Waveforms are always bound to an earthquake (or potentially an
earthquake group) - the natural interpretation being that the waveform recorded
the earthquake.

Every uploaded waveform has to be bound to a preexisting event. To be able to
differentiate waveforms for the same event and the same channel the plugin
currently employs two additional fields per waveform:

* **is_synthetic**: A simple flag
* **tag**: A short tag describing the waveform. The empty tag, by convention, is
  reserved for the raw, recorded waveform.

In the future, the plugin will be expanded to allow for more detailed waveform
descriptions. The current plan is to describe all waveforms (in addition to the
two fields described above) with the help of three files:

* **Station metadata** -> Sufficient to fully describe raw waveforms
* **Processing.xml** -> A (yet-to-be-defined) XML format detailing the (signal)
  processing that has been applied to the waveform. **Not yet implemented**
* **Synthetic.xml** -> A (yet-to-be-defined) XML format detailing the origin of
  the waveform. This mostly means the solver used to generate the waveform, the
  mesh and model it operated on and other parameters. **Not yet implemented**

The combined usage of these three resources and the event they are bound to
should be able to completely describe any waveform that occurs, e.g. in the
course of a tomographic inversion.

## Installation

### Requirements

    * Python 2.7.x
    * seishub.core
    * ObsPy >= 0.8.3
    * PIL (only needed for running the tests)
    * flake8 (only needed for running the tests)

And naturally all dependencies of the listed modules.

### Normal installation

```bash
pip install .
```

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

The event will receive a numerical name if `EVENT_NAME` is not given.

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
* `color`: The facecolor of the beachball (default: `'red'`)

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

#### Get details about a specific station
`GET BASE/event_based_data/station?network=network_code&station=station_code`

**Options:**
* `format`: Determines the format of the list.
    * `xml`: default
    * `json`
    * `xhtml`


## Waveform data

Waveform data can be uploaded in any format supported by ObsPy. Furthermore
every waveform file must be bound to an already existing event. Otherwise, an
error will be raised. SAC files are special in that they contain coordinates.
They will be extracted upon uploading and matched with information coming from
RESP files.

### "RESTful" waveform interface

#### Upload a new waveform file:
`POST BASE/event_based_data/waveform?event=EVENT_NAME`

**Options:**
* `event`: The name of the event (required)
* `synthetic`: Simple true/false flag
* `index_file`: Usually the data of the POST request is uploaded to the server.
    This might not be desireable if exising data structures are not meant to be
    disrupted. To simply index the data, use the `index_file` parameter and
    pass a filepath reachable for the server.
* `tag`: Optional tag for the waveform file. This is an easy way to distinguish
    different files for the same event and channel. If none is given, it will
    result in an empty tag. By convention this means that the data is the raw
    data from the recording station.

#### Get a list of all waveforms for a given event
`GET BASE/event_based_data/waveform?event=EVENT_NAME`

**Options:**
* `format`: Determines the format of the list.
    * `xml`: default
    * `json`
    * `xhtml`

#### Get a list of all waveforms available at a given station
`GET BASE/event_based_data/waveform?event=EVENT_NAME&station_id=NET.STA`

**Options:**
* `format`: Determines the format of the list.
    * `xml`: default
    * `json`
    * `xhtml`

#### Get a waveform file
`GET BASE/event_based_data/waveform?event=EVENT_NAME&channel_id=NET.STA.LOC.CHA`

**Options:**
* `channel_id`: Id of the channel to retrieve in the form *NET.STA.LOC.CHA*
* `tag`: Which tag to retrieve. If none is given it will be interpreted as an
    empty tag. This will, by convention, return the raw data from the recording
    station.
* `format`: The output format (optional). If none is given, the file
    will be returned in the same format as it was originally uploaded in.
    Available choices:
   * `mseed`
   * `sac`
   * `gse2` (Only supported for some data types)
   * `segy` (Only supported for some data types)
   * `raw` - This one is special. It will simply return the raw,
            originally uploaded data. In the case of multicomponent files it
            will return a file containing all these components.
   * `json` - Returns a JSON representation of the data. Very useful for
            plotting inside a web application. Please only use for small time
            series as it is rather verbose and expensive. Will return a JSON
            representation akin to the following:

```json
[
  {
    "sampling_rate": 2.0,
    "channel": "CA.FBR..E",
    "npts": 1500,
    "data": [
      {"value": 0.0, "time": "2009-04-06T01:32:00"},
      {"value": 0.0, "time": "2009-04-06T01:32:00.500000"},
      ...
    ]
  },
  ... next trace ...
]
```


## Misc mappers

Internally files are handled via so called filepath ids. Each one refers to an
existing file. To download it, use the following interface.

`GET BASE/event_based_data/downloadFile?filepath_id=FILEPATH_ID`
