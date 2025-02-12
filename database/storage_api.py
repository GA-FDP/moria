"""
This module contains the StorageAPI class for storing data in the database.
"""

# system
from datetime import datetime

# MORIA
import uuid
from .database  import Database
from .query_api import QueryAPI

class StorageAPI:
    """ Mongo database storage API.

    Parameters
    ----------
    db : Database instance
        The client connection to the database.
    """
    def __init__(self, db: Database):
        self.db = db 
        self.query = QueryAPI(self.db)

        # non-GridFS collection name
        self.acq_collection = "acquisitions"

    # --------------------------------------------------------------------
    # Generalized archive utility using the storage API [single document]
    # --------------------------------------------------------------------
    def insert_data(self, data_struct: dict):
        """ Archive a single document into the database.

        This function will dynamically determine where the data needs to be archived in based on 
        the preference set when the instrument was added to the instruments collection.

        Parameters
        ----------
        data_struct : dict
            Structure containing the measument data and associated metadata for a single 
            device.

        Structure
        ---------
        data_struct = {
                        data : {
                                 'measurement1' : str1/value1/array1,   
                                 'measurement2' : str2/value2/array2,
                                 ...
                               },
                        metadata : { # These metadata fields are required, other metadata is optional.
                                    'shot_number': 		format: int | style: UNIQUE
                                    'experiment':		format: str | style: caps only, underscore delimited
                                    'trigger_timestamp':	format: ISODate format
                                    'archive_timestamp':	format: ISODate format [ datetime.now() ]
                                    'instrument':		format: str | style: caps only, underscore delimited
                                    'diagnostic':		format: str | style: caps only, underscore delimited
                                    'device_name':		format: str | style: MUST BE UNIQUE TO EACH DEVICE
                                    'data_info': {
                                                  ‘field1_name’ : {	
                                                                   ‘data_type’:    format: str
                                                                   ‘units’:	   format: str
                                                                   ‘description’:  format: str
                                                                  }
                                                  ‘field2_name’ : { 
                                                                    … 
                                                                  }}
                                    'notes': 			format: str
                                    ...
                                   }
                      }
        """
        # Return instrument name from the dictionary
        inst = data_struct['metadata']['instrument']
        diag = data_struct['metadata']['diagnostic']

        # Ensure the diagnostic and the instrument labels are currently in the database
        if not self.query.instrument_exists(inst):
            err_string = f'{inst} not found in the database instrument collection'
            raise Exception(err_string)
        elif not self.query.diagnostic_exists(diag):
            err_string = f'{diag} not found in the diagnostic collection'
            raise Exception(err_string)

        # Check if deviece is marked to store data into gridFS
        if (self.query.instrument_in_gridfs(inst)): 
            data = data_struct['data']['buffer']

            # Store the GridFS files
            if(isinstance(data, bytes)):
                data_struct['metadata']['archive_timestamp'] = datetime.now()
                self.db.gridfs.put(data, 
                                   filename = data_struct['metadata']['file_name'], 
                                   metadata = data_struct['metadata'])
            else: # TODO: log
                print(f'\nData stored in GridFS must be a bytes object\n')
        
        else:
            # Create a unique document key overriding the auto-generated one # TODO: construct our own unique ID
            data_struct['_id'] = str(uuid.uuid4())
            
            # Store the document
            data_struct['metadata']['archive_timestamp'] = datetime.now()
            try:
                self.db.database[self.acq_collection].insert_one(data_struct) 
            #   If the record is a duplicate, key: <shot_number> + <device_name> or key: <_id>
            except Exception as e:
                print(e)
