#!/usr/bin/env python3

# system
import sys
from datetime import datetime
from random import uniform
from copy import deepcopy

# Image handling 
import io
from PIL import Image

# MORIA
moria_path = '' # NOTE: location of the MORIA API package on your system
sys.path.insert(0, moria_path)
from database import Database, StorageAPI, QueryAPI, AdminAPI

# Import the mongoDB and associated values
# ----------------------------------------------------------------------------
# Initializes the connection to the server containing the data. server_ip is 
# set to None because I am assuming this is being called from the same server. 
# If not replace with the IP address.
db = Database(db_name = 'test_db', server_ip = None)
storage = StorageAPI(db)
query   = QueryAPI(db)
admin   = AdminAPI(db)

# Get the system arguements
if (len(sys.argv) != 2):
    print('\nUsage: examples.py <test_index>')
    print(' 0: initial setup')
    print(' 1: storage examples')
    print(' 2: query examples')
    exit()
else:
    test_ind = int(sys.argv[1])


# ============================================================================
# TESTING
# ============================================================================

# ----------------------------------------------------------------------------
# ADDING INSTRUMENTS AND DIAGNOSTIC NAMES (required for archiving)
# ----------------------------------------------------------------------------
if (test_ind == 0):
    # Set a default experiment name, this can be called from any code connected
    # to the database
    admin.set_experiment(name = 'TEST_EXP')

    # Only add a couple instruments for example (Make as general as possible)
    admin.add_instrument(instrument = 'GAUGE', gridfs_bool = False)
    admin.add_instrument(instrument = 'CAMERA', gridfs_bool = True)
    admin.add_diagnostic(diagnostic = 'SAMPLE_OUTPUT')

    # Print the current entries in the instruments/diagnostics collections. 
    # Should match the above inputs.
    print(f'{query.get_experiment()}')
    inst_info = query.hardware_info('instruments', print_list = True)
    diag_info = query.hardware_info('diagnostics', print_list = True)


# ----------------------------------------------------------------------------
# STORAGE EXAMPLES
# ----------------------------------------------------------------------------
def image_to_bytes(image_path):
    """Converts an image to bytes."""

    with Image.open(image_path) as img:
        byte_arr = io.BytesIO()
        img.save(byte_arr, format=img.format)
        return byte_arr.getvalue()

if (test_ind == 1):
    # Universal metadata REQUIRED for every device that stores data. Any number 
    # of fields can be added to the dictionaries these are just required. 
    data = {}
    metadata = { 'shot_number':       '', # UNIQUE shot (pulse) indicator
                 'experiment': query.get_experiment(), 
                 'trigger_timestamp': '', # Time in ISODate format when the acquisition is initiated
                 'archive_timestamp': '', # Time when the data is archived
                 'instrument':        '', 
                 'diagnostic':        '', # Diagnostic the device is tied to for this acquisition
                 'device_name':       '', # UNIQUE device identifier
                 'data_info':         {}  # Describes the fields with data
               }

    # Below are a couple examples archiving different types of data. Usually different
    # device data would be archived within different control codes simultaneously for the 
    # same laser pulse (shot), here I am archiving two devices in serial for the same 
    # "shots" for explanatory purposes.

    # Example archiving a gauge for a range of shots
    # Device 1 -- gauge_1
    gauge1_data, gauge1_metadata = deepcopy(data), deepcopy(metadata)

    for shot in range(1, 6):
        # Simulated gauge measurements
        gauge1_data['meas1'] = shot * .37
        gauge1_data['meas2'] = (shot - 1) * .68 

        # Gauge metadata
        gauge1_metadata['shot_number'] = shot
        gauge1_metadata['trigger_timestamp'] = datetime.now()
        gauge1_metadata['device_name'] = 'gauge_1'
        gauge1_metadata['instrument'] = 'GAUGE'         # MUST existinstruments collection
        gauge1_metadata['diagnostic'] = 'SAMPLE_OUTPUT' # MUST exist in the diagnostics collection
        gauge1_metadata['data_info'] = { 'meas1' : { 'data_type' : 'float',
                                                     'units' : 'seconds',
                                                     'description' : 'example measurement 1'
                                                 },
                                         'meas2' : { 'data_type' : 'float',
                                                     'units' : 'Coulombs',
                                                     'description' : 'example measurement 2'
                                                   }
                                       }
        # Archive step
        gauge1_metadata['archive_timestamp'] = datetime.now()
        data_struct = {'data': gauge1_data, 'metadata': gauge1_metadata}
        try:
            storage.insert_data(data_struct)
        except Exception as e:
            print(e)


    # Example archiving camera data for a range of shots
    # Device 2 -- basler_1
    basler1_data, basler1_metadata = deepcopy(data), deepcopy(metadata)
    for shot in range(1, 4):
        # Simulated camera acquisitions (use the test images)
        image_path = 'sample_images'
        if (shot == 1): file_name = 'forest.jpg'
        if (shot == 2): file_name = 'm83.tif'
        if (shot == 3): file_name = 'mountain.jpg'
        
        basler1_metadata['file_name'] = file_name
        basler1_data['buffer'] = image_to_bytes(f'{image_path}/{file_name}')

        # Camera metadata
        basler1_metadata['shot_number'] = shot
        basler1_metadata['trigger_timestamp'] = datetime.now()
        basler1_metadata['device_name'] = 'basler_1'
        basler1_metadata['instrument'] = 'CAMERA'        # MUST exist in the instruments collection
        basler1_metadata['diagnostic'] = 'SAMPLE_OUTPUT' # MUST exist in the diagnostics collection
        basler1_metadata['data_info'] = { 'image' : { 'data_type' : 'GridOut', # GridFS file output
                                                      'units' : '',
                                                      'file_type' : file_name[-3:],
                                                      'description' : 'recorded image sharded by GridFS'
                                                    }
                                        }
        # Archive step
        basler1_metadata['archive_timestamp'] = datetime.now()
        data_struct = {'data': basler1_data, 'metadata': basler1_metadata}
        try:
            storage.insert_data(data_struct)
        except Exception as e:
            print(e)


# ----------------------------------------------------------------------------
# QUERY BUILDER EXAMPLES
# ----------------------------------------------------------------------------
if (test_ind == 2):
    # In order to get data from the database you need to first construct a 
    # query. The way this is done is by submitting value or range query 
    # dictionaries into the appropriate functions. These functions are submitted 
    # to the current filter pipeline and used when run_query is called. Multiple 
    # calls of the functions with different filter criteria can be used in 
    # succession and will be treated as additional database filters. To clear
    # the current filter_pipeline run clear_query().

    # Using make_dict with run_query returns a user friendly dictionary containing 
    # the documents that fit the criteria for each unique device_name. Otherwise
    # it returns a MongoDB cursor object that then needs to be parsed.

    # NOTE: There are additional direct GridFS queries included in the API.
    #       They are pretty limited and rather straightforward.

   
    # Single value query returning the camera data with the associated values
    # for a single shot.
    # ------------------------------------------------------------------------
    device_name = 'basler_1'
    value_query_dict = { 'metadata' : { 'device_name' : [device_name],
                                        'shot_number' : [1]
                                      }
                       }
    # Run query
    query.query_data_value(value_query_dict)
    res = query.run_query(fetch_related_data = False, make_dict = True)

    # View image 
    print(res[device_name][0]['metadata'])  # document metadata
    mongo_img = res[device_name][0]['data'] # actual file in MongoDB format 
    query.view_image(mongo_img)
   
    # Clear the query pipeline
    query.clear_query()
    print('')


    # Range query returning not only the values that fit the query but the 
    # data from other devices corresponding to the same shots.
    # ------------------------------------------------------------------------
    range_query_dict = { 'metadata' : { 'shot_number' : [1, 3] }, 
                         'data' : { 'meas1' : [0.5, 1.5] }
                       } 

    # Run query 
    query.query_data_range(range_query_dict)
    res = query.run_query(fetch_related_data = True, make_dict = True)

    # Print the resultant dictionary
    # Output: Should be the gauge_1 and basler_1 documents corresponding to shots 2 & 3 
    for device in res:
        device_list = res[device]

        print(f'\n{device} documents')
        print('----------------------------------')
        for doc in device_list: print(doc)

    # Clear the query pipeline
    query.clear_query()
    print('')


    # Combination range and value query.
    # ------------------------------------------------------------------------
    value_query_dict = { 'metadata' : {'instrument' : ['GAUGE']} }
    range_query_dict = { 'metadata' : {'shot_number' : [3, 4]} } 

    # Run query 
    query.query_data_value(value_query_dict)
    query.query_data_range(range_query_dict)
    res = query.run_query(fetch_related_data = False, make_dict = True)

    # Print the resultant dictionary
    # Output: Should be the basler_1 documents corresponding to shots 3 & 4 
    for device in res:
        device_list = res[device]

        print(f'\n{device} documents')
        print('----------------------------------')
        for doc in device_list: print(doc)
