"""
This module contains the QueryAPI class for querying the database.
"""

# image data
import io
import numpy as np
from PIL import Image

# date/time
import time
from dateutil import parser as datetime_parser

# MORIA
from .database import Database

class GaladrielDatabaseException(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self) -> str:
        return self.message


class QueryAPI:
    def __init__(self, db: Database):
        self.db = db

        # debug
        self.debug = 0 

        # For query building
        self.filter_pipeline = []

        # Collections containing data
        self.collections = ['acquisitions', 'fs.files']
        self.dict_names  = ['acq', 'gridfs']            # used in aggregation queries

        # Useful global values
        self.num_collections = len(self.collections)
        self.data_collection = self.collections[0]
        self.gridFS_collection = self.collections[1]     
        

    ##################################################################################
    ###                         Query builder interface                            ###
    ##################################################################################

    # CLEAR THE BUILT QUERY
    # --------------------------------------------------------------------------------
    def clear_query(self):
        self.filter_pipeline.clear()

    # EXECUTE THE BUILT QUERY
    # --------------------------------------------------------------------------------
    # Run one single aggregation query that filters each collection and returns the output
    def run_query(self, fetch_related_data = False, make_dict = True):
        key = 'metadata.shot_number'
        
        if (fetch_related_data):
            # Match and group by key
            self.filter_pipeline.append({ '$group': { '_id': f'${key}' }})
            
            # Initialize the union pipeline using the filter pipeline
            union_pipeline = self.filter_pipeline.copy()

            # Include keys from the other collections that match the search criteria
            for i in range(1, self.num_collections):
                union_pipeline.extend([{ '$unionWith': { 'coll': self.collections[i],
                                                         'pipeline': self.filter_pipeline
                                                       }
                                       },

                                       # Ensure uniqueness after union
                                       {
                                         '$group': { '_id': '$_id' }
                                       }])
            
            # Lookup the data from each collection corresponding to the list of keys
            for name, collection in zip(self.dict_names, self.collections):
                union_pipeline.extend([{ '$lookup': { 'from': collection,
                                                      'localField': '_id',
                                                      'foreignField': key,
                                                      'as': name
                                                    }
                                       }])
        else: # Only apply a filter to each collection 
            union_pipeline = self.filter_pipeline.copy()
            
            for i in range(1, self.num_collections):
                union_pipeline.extend([{ '$unionWith': { 'coll': self.collections[i],
                                                         'pipeline': self.filter_pipeline 
                                                       }
                                       }])
        # Debug        
        if (self.debug > 0): 
            print(f'\nFilter pipeline:\n{self.filter_pipeline}')
            print(f'\nUnion pipeline:\n{union_pipeline}\n')

        # Run the aggregation query 
        res_cursor = self.db.database[self.data_collection].aggregate(union_pipeline)

        # Return the results
        # ------------------------------------
        # NOTE: this step is merely to create a user friendly dictionary and is not strictly
        #       necessary, disable if faster speeds are required
        if (make_dict): return self.create_dict(res_cursor, fetch_related_data)
        else: return res_cursor


    # BUILD THE QUERY PIPELINE [ Filters the database ]
    # --------------------------------------------------------------------------------
    def query_data_range(self, query_dict: dict):
        match_input = {"$match" : {"$and" : []}}
        
        # Create the query filter from the query dictionary 
        for data_type, data_dict in query_dict.items():
            for field, query_list in data_dict.items():

                # Check if the list is empty
                q_len = len(query_list)
                if (q_len == 0): 
                    print(f'\nERROR in {field}: query list is empty\n') 
                    continue
                    
                # Return the requested bounds for the field
                lower_bound, upper_bound = query_list[0], query_list[1]

                #  time queries [Ex. 2024-01-01 00:00:00 ]
                if (isinstance(lower_bound, str) and isinstance(upper_bound, str)):
                    try:
                        lower_bound = datetime_parser.parse(lower_bound)
                        upper_bound = datetime_parser.parse(upper_bound)
                        if (lower_bound > upper_bound):
                            print(f'\nERROR in {field}: {lower_bound} is after {upper_bound}\n') 
                            continue
                    except ValueError:
                        print(f'\nERROR in {field}: string bounds [{lower_bound}, {upper_bound}] ' + \
                              f'are not parsable by datetime\n') 
                        continue
                
                #  numerical queries
                elif (isinstance(lower_bound, (int, float)) and isinstance(upper_bound, (int, float))):
                    if (lower_bound > upper_bound):
                        print(f'\nERROR in {field}: lower bound ({lower_bound}) > upper bound ({upper_bound})\n') 
                        continue

                else:
                    print(f'\nERROR in {field}: the upper and lower bounds ' + \
                          f'[{lower_bound}, {upper_bound}] are in incompatible formats\n')
                    continue

                match_input["$match"]["$and"].append({f"{data_type}.{field}" : {"$gte" : lower_bound, "$lte" : upper_bound}})

        # Add to pipeline
        if (len(match_input["$match"]["$and"]) != 0): self.filter_pipeline.append(match_input)


    def query_data_value(self, query_dict: dict):
        match_input = {"$match" : {"$and" : [ {"$or" : []} ]}}

        # Create the query filter from the query dictionary 
        for data_type, data_dict in query_dict.items():
            for field, query_list in data_dict.items():
                # Check if the list is empty
                q_len = len(query_list)
                if (q_len == 0):
                    print(f'\nERROR in {field}: query list is empty\n') 
                    continue

                for q_ind in range(q_len):
                    # Allow for OR arguments on some select fields
                    if (field in ["experiment", "diagnostic", "instrument", "device_name"]) and (q_len > 1):
                        match_input["$match"]["$and"][0]["$or"].append({f"{data_type}.{field}" : query_list[q_ind]})
                    else:
                        match_input["$match"]["$and"].append({f"{data_type}.{field}" : query_list[q_ind]})

        # Check if the query lists are empty
        #  - OR
        if (len(match_input["$match"]["$and"][0]["$or"]) == 0): match_input["$match"]["$and"].pop(0)
        #  - AND
        if (len(match_input["$match"]["$and"]) != 0): self.filter_pipeline.append(match_input)


    # CREATE USER FRIENDLY DICTIONARY 
    # --------------------------------------------------------------------------------
    def add_dict_value(self, res_doc: dict):
        inst = res_doc["metadata"]["instrument"]
        dev  = res_doc["metadata"]["device_name"]

        # Ensure the dictionary keys are added
        if dev not in self.query_dict.keys(): self.query_dict[dev] = []

        # Add the matching data structures to the output dictionary
        if (self.instrument_in_gridfs(inst)):
            doc_struct = {}
            try:
                # Retrieve the file using GridOut
                file_id = res_doc["_id"]
                grid_out = self.db.gridfs.get(file_id)

                # Create the corresponding data structure
                doc_struct["_id"] = file_id
                doc_struct["data"] = grid_out
                doc_struct["metadata"] = res_doc["metadata"]
                self.query_dict[dev].append(doc_struct)
            except:
                return 
        else:
            self.query_dict[dev].append(res_doc)
    

    def create_dict(self, query_result, fetch_related_data: bool) -> dict:
        # Initialize the output dictionary
        self.query_dict = {}
        
        # Loop through each document from each collection in the cursor
        for doc in query_result:
            if (fetch_related_data):

                for name in self.dict_names:
                    num_docs = len(doc[name]) # number of documents returned from the collection
                    for i in range(num_docs): self.add_dict_value(doc[name][i])
            
            else:
                self.add_dict_value(doc)
        
        return self.query_dict


    ##################################################################################
    ###                         Direct MongoDB queries                             ###
    ##################################################################################
    def get_last_shot_number(self):
        return self.db.database["run_setup"].distinct("last_shot")[0]

    def get_experiment(self):
        return self.db.database["run_setup"].distinct("experiment")[0]

    def diagnostic_exists(self, diagnostic: str):
        num_docs = self.db.database["diagnostics"].count_documents({"diagnostic": diagnostic})
        return num_docs == 1

    def instrument_exists(self, instrument: str):
        num_docs = self.db.database["instruments"].count_documents({"instrument": instrument})
        return num_docs == 1

    def instrument_in_gridfs(self, instrument: str):
        if not self.instrument_exists(instrument): 
            print("\nInstrument doesn't exist\n")
            return

        cursor = self.db.database["instruments"].find({"instrument": instrument})
        instrument_info = cursor.next()
        return instrument_info["gridfs"]

    def hardware_info(self, dev_type: str, print_list = False):
        if (dev_type != "instruments") and (dev_type != "diagnostics"):
            print("Not a valid input [instruments/diagnostics]")
            return
        
        dev_list = []
        dev_cursor = self.db.database[dev_type].find()
        num_dev = self.db.database[dev_type].count_documents({})

        if (print_list): print(f"\n{dev_type} currently in the database")
        if (print_list): print("---------------------------------")
        for i in range(num_dev):
            dev = dev_cursor.next()
            dev_val = dev[dev_type[:-1]]
            if (print_list): print(f' - {dev_val}')
            dev_list.append(dev_val)
        if (print_list): print("---------------------------------\n")

        return dev_list

    def get_device_fields(self, device_name: str):
        data_dict = 'metadata'
        filter_crit = {f'{data_dict}.device_name': device_name}
        sort_crit   = [(f'{data_dict}.shot_number', -1)]     # Most recent document
        
        doc_stores = [self.data_collection, self.gridFS_collection]

        # Search both collections if necessary
        for collection in doc_stores:
            document = self.db.database[collection].find_one(filter_crit, sort = sort_crit)
            if (document):
                print(document['metadata']['shot_number'])
                return list(document['metadata'].keys())
    
        return []


    ##################################################################################
    ###                         Direct GridFS queries                              ###
    ##################################################################################
    def get_by_metadata(self, key: str, value: any):
        cursor = self.db.gridfs.find(filter={"metadata." + key: value})
        files = [f.read() for f in cursor]
        return files

    def get_by_filename(self, filename: str):
        cursor = self.db.gridfs.find(filter={"filename": filename})
        files = [f.read() for f in cursor]
        return files[0]

    def get_in_time_range(self, date_a: str, date_b: str):
        self.upload_time = "metadata.trigger_timestamp" # time parameter to query on
        date_a = datetime_parser.parse(date_a)
        date_b = datetime_parser.parse(date_b)
        cursor = self.db.gridfs.find({self.upload_time: {"$gte": date_a, "$lte": date_b}})
        return [f for f in cursor]


    ##################################################################################
    ###                 GridFS Image handling/read functions                       ###
    ##################################################################################

    # gridfs_file = <gridfs.grid_file.GridOut object at 0x14776e00df10>

    def get_metadata_from_cursor(self, gridfs_file):
        metadata = gridfs_file.metadata
        return metadata

    def convert_gridfs_file_to_image(self, gridfs_file):
        gridfs_file.seek(0)
        image_bytes = gridfs_file.read()
        image_stream = io.BytesIO(image_bytes)

        # TODO: consider putting image format in metadata:
        image = Image.open(image_stream, mode="r", formats=["TIFF"])
        return image
    
    def read_image(self, gridfs_file):
        return self.convert_gridfs_file_to_image(gridfs_file)

    def image_to_nparray(self, gridfs_file):
        image = self.convert_gridfs_file_to_image(gridfs_file)
        return np.array(image)

    def view_image(self, gridfs_file):
        image = self.convert_gridfs_file_to_image(gridfs_file)
        norm_image = self.normalize_image(image)
        norm_image.show(title=gridfs_file.filename)

    def save_image_to_file(self, gridfs_file):
        # get the data
        image = self.convert_gridfs_file_to_image(gridfs_file)
        metadata = self.get_metadata_from_cursor(gridfs_file)
        
        # create files
        image_name = gridfs_file.filename
        metadata_name = gridfs_file.filename + ".metadata"
        
        # save image 
        image.save(image_name)

        # save corresponding metadata
        with open(metadata_name, 'w') as data: data.write(str(metadata))

    def normalize_image(self, image):
        # convert the 16-bit image to 8-bit so it can be shown using a viewer
        return image.convert('RGB')
