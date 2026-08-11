"""
This module contains the StorageAPI class for storing data in the database.
"""

# system
import pickle
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

        # non-GridFS collection names
        self.acq_collection  = "acquisitions"
        self.proc_collection = "processed_data"

    # -----------------------------------------------------------------------------------
    # Generalized archive utility using the storage API [single document]
    # -----------------------------------------------------------------------------------
    def insert_data(self, data_struct: dict, processed_data = False, store_in_gridfs = False):
        """ Archive a single document into the database.

        This function will dynamically determine where the data needs to be archived in based on 
        the preference set when the instrument was added to the instruments collection.

        Parameters
        ----------
        data_struct : dict
            Structure containing the measument data and associated metadata for a single 
            device.
        
        processed_data : bool
            If this flag is enabled the data will be stored in the processed_data collection
            instead of the raw data acquisition or gridFS.

        store_in_gridfs : bool
            This is to override the instrument table and archive this document into gridFS.

        Structure
        ---------
        raw_data_struct = {
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
        
        processed_data_struct = {
                        data : {
                                 'analysis1' : str1/value1/array1,   
                                 'analysis2' : str2/value2/array2,
                                 ...
                               },
                        metadata : { # These metadata fields are required, other metadata is optional.
                                    'shot_number'                 format: int 
                                    'experiment':		  format: str | style: caps only, underscore delimited
                                    'archive_timestamp':	  format: ISODate format [ datetime.now() ]
                                    'diagnostic' OR 'process':    format: str | style: underscore delimited
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

        # Split struct into data and metadata
        # -------------------------------------------------------------------------------
        data, metadata = data_struct['data'], data_struct['metadata']

        # Store the data in the appropriate collection
        # -------------------------------------------------------------------------------
        # ========= Processed optimization, experimental run data =========
        
        # Check if the dictionary contains raw data
        if processed_data:
            # Ensure the required fields exist
            # -------------------------------------------------------------
            req_fields = ['shot_number', 'experiment']
            for field in req_fields:
                if field not in metadata: 
                    raise Exception(f'ERROR: Metadata is missing the {field} field')
            
            # Ensure the strictly not required fields don't exist
            # -------------------------------------------------------------
            nreq_fields = ['instrument', 'device_name']
            for field in nreq_fields:
                if field in metadata: 
                    raise Exception(f'ERROR: Metadata contains the {field} field, rename or remove field from the dict')

            # Ensure the required fields are valid
            # -------------------------------------------------------------
            shot, exp = metadata['shot_number'], metadata['experiment'] 
            if not isinstance(shot, int): 
                raise Exception(f'ERROR: {shot} is not a valid shot_number, must be integer valued')
            if not isinstance(exp, str) or not exp:
                raise Exception(f'ERROR: {exp} is not a valid experiment name, must be a non-empty string')
            
            if 'diagnostic' in metadata:
                diag = metadata['diagnostic']
                if not self.query.diagnostic_exists(diag):
                    raise Exception(f'ERROR: {diag} not found in the database diagnostic collection')
            elif 'process' in metadata:
                proc = metadata['process']
                if not isinstance(proc, str) or not proc: 
                    raise Exception(f'ERROR: {proc} is not a valid experiment name, must be a non-empty string')
            else:
                raise Exception('ERROR: Metadata is missing a descriptive field [diagnostic OR process]')

            # Create a unique document key overriding the auto-generated one # TODO: construct our own unique ID
            data_struct['_id'] = str(uuid.uuid4())
            
            # Store the data
            try:
                metadata['archive_timestamp'] = datetime.now()
                self.db.database[self.proc_collection].insert_one(data_struct) 
            #   If the record is a duplicate, key: <shot_number> + <device_name> or key: <_id>
            except Exception as e:
                print(e)


        # =========================== Raw data ============================
        else:
            # Ensure the required fields exist
            # -------------------------------------------------------------
            req_fields = ['shot_number', 'trigger_timestamp', 'instrument', 'diagnostic', 'device_name', 'experiment']
            for field in req_fields:
                if field not in metadata: 
                    raise Exception(f'ERROR: Metadata is missing the {field} field')

            # Return field values from the dictionary
            # -------------------------------------------------------------
            shot, trig_time = metadata['shot_number'], metadata['trigger_timestamp']
            inst, diag = metadata['instrument'], metadata['diagnostic']
            dev, exp = metadata['device_name'], metadata['experiment']

            # Ensure the required fields are valid
            # -------------------------------------------------------------
            if not isinstance(shot, int): 
                raise Exception(f'ERROR: {shot} is not a valid shot_number, must be integer valued')
            
            #  Ensure the diagnostic and the instrument labels are currently in the database
            if not self.query.instrument_exists(inst):
                err_string = f'ERROR: {inst} not found in the database instrument collection'
                raise Exception(err_string)
            
            elif not self.query.diagnostic_exists(diag):
                err_string = f'ERROR: {diag} not found in the database diagnostic collection'
                raise Exception(err_string)

            #  Ensure that the other fields are non-empty strings
            if not isinstance(dev, str) or not dev: 
                raise Exception(f'ERROR: {dev} is not a valid device name, must be a non-empty string') 
            if not isinstance(exp, str) or not exp: 
                raise Exception(f'ERROR: {exp} is not a valid experiment name, must be a non-empty string') 

            # Check if device is marked to store data into gridFS
            # -------------------------------------------------------------
            if (self.query.instrument_in_gridfs(inst)): # Camera images 
                data = data['buffer']

                # Store the GridFS files
                if(isinstance(data, bytes)):
                    metadata['archive_timestamp'] = datetime.now()
                    self.db.gridfs.put(data, 
                                       filename = metadata['file_name'], 
                                       metadata = metadata)
                else: # TODO: log
                    print(f'\nData stored in GridFS must be a bytes object\n')
        
            elif (store_in_gridfs): # Other files
                # Convert data dictionary to byte stream
                data = pickle.dumps(data)

                metadata['archive_timestamp'] = datetime.now()
                self.db.gridfs.put(data,
                                   filename = '',
                                   metadata = metadata)

            else:
                # Create a unique document key overriding the auto-generated one # TODO: construct our own unique ID
                data_struct['_id'] = str(uuid.uuid4())
            
                # Store the document
                metadata['archive_timestamp'] = datetime.now()
                try:
                    self.db.database[self.acq_collection].insert_one(data_struct) 
                except Exception as e:
                    print(e)
