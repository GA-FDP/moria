# moria
## Archive Information

```
# skeleton data dictionaries (which need to be filled)
self.data = {...}
self.metadata = {'shot_number':       "", # format: int
                 'experiment':        "", # format: str | style: caps only, underscore delimited
                 'trigger_timestamp': "", # format: ISODate format
                 'archive_timestamp': "", # format: ISODate format [ datetime.now() ]
                 'instrument':        "", # format: str | style: caps only, underscore delimited
                 'diagnostic':        ""  # format: str | style: caps only, underscore delimited
                 'device_name':       "", # format: str | style: lowercase + last 4 digits of serial number, underscore delimited 
                 ...
                }

# what you store using insert_data from the storage API
data_struct = {'data': self.data, 'metadata': self.metadata}
```
