## API Definition

`BASE` always refers to the base SeisHub URL of the server including the port
number. Most data is bound to a certain event. In that case the event argument
in the form `event=EVENT_NAME` is appended to the url. This in unified across
all event bound data types.

### Station data

Station data is not bound to any event as it is potentially shared between many
events. Currently the following file formats are accepted:

* RESP
* SEED
* XML-SEED


#### Upload a new station:
`POST BASE/event_based_data/station`

#### Get a list of all stations
`GET BASE/event_based_data/station`

#### Get the originally uploaded file of one specific station resource
`GET BASE/event_based_data/station/STATION_NAME`


### Event data

Most data is, as the plug-in name implies bound to a certain event. Thus
uploading a new event is always the first step. Currently only the QuakeML
format is accepted.

#### Upload a new, unnamed event
`POST BASE/event_based_data/event`
    which is just an alias for
`POST BASE/xml/event_based_data/event'

#### Upload a new, named event
`POST BASE/event_based_data/event/EVENT_NAME`
    which is just an alias for
`POST BASE/xml/event_based_data/event/EVENT_NAME`


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
