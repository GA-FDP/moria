#!/usr/bin/env python3

# system
import os
import pwd
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
db = Database(db_name = 'moria_test', server_ip = None)
storage = StorageAPI(db)
query   = QueryAPI(db)
admin   = AdminAPI(db)

# Get the system arguements
if (len(sys.argv) != 2):
    print('\nUsage: examples.py <test_index>')
    print(' 0: initial setup')
    print(' 1: storage examples')
    print(' 2: query examples')
    print(' 3: update examples\n')
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
   
    # Universal metadata REQUIRED for every device that stores data into the acquisitions collection. 
    # Any number of fields can be added to the dictionaries these are just required. 
    data = {}
    metadata = { 'shot_number':       '', # UNIQUE shot (pulse) indicator
                 'experiment': query.get_experiment(), 
                 'trigger_timestamp': '', # Time in ISODate format when the acquisition is initiated
                 'archive_timestamp': '', # Time when the data is archived
                 'instrument':        '', 
                 'diagnostic':        '', # Diagnostic the device is tied to for this acquisition
                 'device_name':       '', # UNIQUE device identifier
                 'data_info':         {}, # Describes the fields with data
                 'notes':             []  # Contains individual document comments
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
        data_struct = {'data': basler1_data, 'metadata': basler1_metadata}
        try:
            storage.insert_data(data_struct)
        except Exception as e:
            print(e)

    # -----------------------------------------------------------------------------------------

    # Universal metadata REQUIRED for every device that stores data intermediate analysis 
    # into the processed_data collection. Any number of fields can be added to the dictionaries 
    # these are just required. 
    p_data = {}
    p_metadata = { 'shot_number':       '', # UNIQUE shot (pulse) indicator
                   'experiment': query.get_experiment(), 
                   'archive_timestamp': '', # Time when the data is archived
                   'data_info':         {}, # Describes the fields with data
                   'notes':             []  # Contains individual document comments
               }

    # Example archiving analyzed diagnostic data from a shot # TODO
    # Diagnostic 1 -- diag_1
    diag1_data, diag1_metadata = deepcopy(p_data), deepcopy(p_metadata)
    exp_meas = []
    for shot in range(1, 6): 
        # Simulated diagnsotic analysis
        diag1_data['diag_analysis1'] = shot * uniform(0, 1)
        diag1_data['diag_analysis2'] = (shot - 1) * uniform(0, 1) 
        exp_meas.append(diag1_data['diag_analysis1']) 
        
        # Analysis metadata
        diag1_metadata['shot_number'] = shot
        diag1_metadata['diagnostic'] = 'SAMPLE_OUTPUT' # REQUIRED & must exist in the diagnostics collection
        diag1_metadata['data_info'] = { 'meas1' : { 'data_type' : 'float',
                                                     'units' : 'seconds',
                                                     'description' : 'example measurement 1'
                                                 },
                                        'meas2' : { 'data_type' : 'float',
                                                     'units' : 'Coulombs',
                                                     'description' : 'example measurement 2'
                                                   }
                                       }
        # Archive step
        data_struct = {'data': diag1_data, 'metadata': diag1_metadata}
        try:
            storage.insert_data(data_struct, True) # processed data flag
        except Exception as e:
            print(e)

        
        if (shot == 4):
            # Example archiving intermediate experiment data that occured during the experiment 
            # over a batch of shots # TODO
            # Experimental analysis 1 -- proc_1
            proc1_data, proc1_metadata = deepcopy(p_data), deepcopy(p_metadata)
            proc1_data['exp_raw_data1'] = exp_meas
            proc1_data['exp_analysis1'] = sum(exp_meas) / len(exp_meas) # calculate average over shot range

            # Analysis metadata
            proc1_metadata['shot_number'] = shot
            proc1_metadata['shot_range'] = [1, shot]
            proc1_metadata['process'] = 'experimental_average' # REQUIRED 
            proc1_metadata['data_info'] = { 'analysis1' : { 'data_type' : 'float',
                                                    'units' : 'seconds',
                                                    'description' : 'average over shot range'
                                                  }}
            # Archive step
            data_struct = {'data': proc1_data, 'metadata': proc1_metadata}
            try:
                storage.insert_data(data_struct, True) # processed data flag
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

    # NOTES: 
    #   Range queries must be numeric list with a start and end. 
    #   Value queries must be a list even if only one value is requested.
    # 
    #   There are additional direct GridFS queries included in the API.
    #   They are pretty limited and rather straightforward.
  

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
    raw_res, proc_res = query.run_query(fetch_related_data = False, make_dict = True)

    # View image 
    print(f'\nEXAMPLE 1: image document')
    print('----------------------------------')
    print(raw_res[device_name][0]['metadata'])  # document metadata
    mongo_img = raw_res[device_name][0]['data'] # actual file in MongoDB format 
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
    raw_res, proc_res = query.run_query(fetch_related_data = True, make_dict = True)

    # Print the resultant dictionary
    # Output: Should be the gauge_1 and basler_1 documents corresponding to shots 2 & 3 
    for device in raw_res:
        device_list = raw_res[device]

        print(f'\nEXAMPLE 2: {device} documents')
        print('----------------------------------')
        for doc in device_list: print(doc)
    
    # Print the processed data dictionary
    for diag in proc_res:
        diag_list = proc_res[diag]

        print(f'\nEXAMPLE 2: {diag} analysis')
        print('----------------------------------')
        for doc in diag_list: print(doc)

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
    raw_res, proc_res = query.run_query(fetch_related_data = False, make_dict = True)

    # Print the resultant dictionary
    # Output: Should be the basler_1 documents corresponding to shots 3 & 4 
    for device in raw_res:
        device_list = raw_res[device]

        print(f'\nEXAMPLE 3: {device} documents')
        print('----------------------------------')
        for doc in device_list: print(doc)


# ----------------------------------------------------------------------------
# UPDATE EXAMPLES
# ----------------------------------------------------------------------------
if (test_ind == 3):
    # Below are examples showing how to update/insert new information into previously
    # archived data. The update dictionary is of the same structure as the filter
    # dictionaries, EXCEPT the entry value is not required to be a list but 
    
    # NOTES: 
    #   The update option CAN/WILL overwrite field data and is irreversible. So be very 
    #   careful when choosing the filters for the update query. Try to make them 
    #   as specific as possible or keep them to individual documents (shot number, device name)
    #   to avoid overwritting vast quanities of documents.
    #
    #   There are three seperate commands:
    #       replace: It will replace the value in the document with the value
    #                in the document(s) update dictionary where the fields match.
    #
    #       insert:  It will add a new field, value pair to the document(s). If the 
    #                field exists it will overwrite the current entry.
    #
    #       append:  It will append the value found in the update dictionary to
    #                the document(s) dict/list value where the fields match.
    #   
    #   The update dictionary is of the same structure as the filter dictionaries, 
    #   EXCEPT the entry value is NOT required to be a list, however it can be an int/float, 
    #   an array of values, a dictionary or whatever else.
    # 
    #   Run each of these queries seperately. Uncomment the one you want to try out.


    # Range query replacing the experiment name for the specific shots.
    # As per the other examples we can submit more filters.
    # Output: Should return "3 documents updated." | 1 camera docs and 2 acquisition docs
    # ------------------------------------------------------------------------
    value_filter_dict = {}
    range_filter_dict = { 'metadata' : {'shot_number' : [3, 4]} }
    update_dict = { 'metadata': {'experiment' : 'TEST_EXP2'} }

    admin.update_doc(update_dict, value_filter_dict, range_filter_dict, command = 'replace')
  

    # Single value query to insert a new array measurment as a new data field 
    # in a single document [shot number and device_name]
    # Output: Should return "1 documents updated." | 1 acquisition doc
    # ------------------------------------------------------------------------ 
    value_filter_dict = { 'metadata' : { 'device_name' : ['gauge_1'],
                                         'shot_number' : [5]
                                       }
                        }
    range_filter_dict = {}
    update_dict = { 'data': {'meas_array' : [1, 2, 3, 4, 5, 6]} }

    # admin.update_doc(update_dict, value_filter_dict, range_filter_dict, command = 'insert')


    # Single value query appending a dictionary to provide information about the 
    # field added in the prior example.
    # Output: Should return "1 documents updated."
    # ------------------------------------------------------------------------ 
    update_dict = { 'metadata' : { 'append_to' : 'dict', # list or dict
                                   'data_info' : { 'meas_array' : {
                                                      'data_type' : 'array[int]',
                                                      'units' : 'seconds',
                                                      'description' : 'example measurement array' }
                                                 }
                                 }
                  }

    # admin.update_doc(update_dict, value_filter_dict, range_filter_dict, command = 'append')


    # Single value query appending a dictionary to a list containing a comment about 
    # the previous updates.
    # Output: Should return "1 documents updated."
    # ------------------------------------------------------------------------ 
    # admin.add_note_to_doc(4, 'gauge_1', 'test note describing some additional information') 
    
    # NOTE: same as running 
    # update_dict = { 'metadata' : { 'append_to' : 'list',
    #                                'notes' : { 'created_by' : pwd.getpwuid(os.getuid()).pw_name,
    #                                            'date' : datetime.now(),
    #                                            'content' : 'Added a description about the new field'
    #                                          }
    #                              }
    #               }

    # admin.update_doc(update_dict, value_filter_dict, range_filter_dict, command = 'append')
