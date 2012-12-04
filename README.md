## API Definition

`BASE` always refers to the base SeisHub URL of the server including the port
number.

### Station data

Station data is not bound to any event as it is potentially shared between many
events. Currently the following file formats are accepted:

* RESP
* SEED
* XML-SEED


#### Upload a new station:
`POST BASE/event_based_data/resource/station`

#### Get a list of all stations
`GET BASE/event_based_data/resource/station`

#### Get the originally uploaded file of one specific station resource
`GET BASE/event_based_data/resource/station/STATION_NAME`


### Event data

Most data is, as the plug-in name implies bound to a certain event. Thus
uploading a new event is always the first step. Currently only the QuakeML
format is accepted.

#### Upload a new, unnamed event
`POST BASE/event_based_data/resource/event`
    which is just an alias for
`POST BASE/xml/event_based_data/event'

#### Upload a new, named event
`POST BASE/event_based_data/resource/event/EVENT_NAME`
    which is just an alias for
`POST BASE/xml/event_based_data/event/EVENT_NAME`


### Waveform data

All waveform formats supported by ObsPy can be uploaded. Every waveform needs
to be bound to an already existing event

#### Upload a new waveform file:
`POST BASE/event_based_data/resource/event/waveform`

#### Get a list of all waveform for a given event
`GET BASE/event_based_data/resource/event/waveform`
