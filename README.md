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
`POST BASE/resource/station`

#### Get a list of all stations
`GET BASE/resource/station`

#### Get the originally uploaded file of one specific station resource
`GET BASE/resource/station/STATION_NAME`
