"""
This module contains the AdminAPI class for database administration tasks.
"""

# System imports
import os
import pwd
from datetime import datetime

from .database  import Database
from .query_api import QueryAPI

class AdminAPI:
    """ Mongo database administration API.

    Allows basic manipulation of the database for various applications.

    Parameters
    ----------
    db : Database instance
        The client connection to the database.
    """
    def __init__(self, db: Database):
        self.db = db
        self.query = QueryAPI(self.db)

    # Instrument collection
    # ---------------------------------------------------------------------------
    def add_instrument(self, instrument: str, gridfs_bool: bool):
        """ Add a new instrument to the instruments collection.

        Parameters
        ----------
        instrument : str 
            The instrument name. Should correspond to a general purpose 
            classification of instrument type (i.e. CAMERA).

        gridfs_bool : bool, default=None
            If True, the documents the are archived will be stored 
            using GridFS. The data will be sharded in fs.chunks and the metadata
            will be archived in fs.files an will contain information to reassemble
            the sharded chunks.
        """
        if self.query.instrument_exists(instrument):
            print("\nInstrument already exists\n")
        elif not isinstance(instrument, str):
            print("\nInstrument variable must be a string\n")
        elif not isinstance(gridfs_bool, bool):
            print("\nSecond input must be a boolean variable: True/False\n")
        else:
            self.db.database["instruments"].insert_one({'instrument':instrument, 'gridfs':gridfs_bool})

    def remove_instrument(self, instrument: str):
        """ Removes an instrument from the instruments collection.

        Parameters
        ----------
        instrument : str 
            The name of a valid instrument stored in the instruments collection.
        """
        if not self.query.instrument_exists(instrument):
            print("\nInstrument doesn't exist\n")
        elif not isinstance(instrument, str):
            print("\nInstrument variable must be a string\n")
        else:
            self.db.database["instruments"].delete_one({'instrument':instrument})


    # Diagnostic collection
    # ---------------------------------------------------------------------------
    def add_diagnostic(self, diagnostic: str):
        """ Add a new diagnostic to the diagnostics collection.

        Parameters
        ----------
        diagnostic : str 
            The diagnostic name. Should correspond to a general commonly used 
            diagnostic.
        """
        if self.query.diagnostic_exists(diagnostic):
            print("\nDiagnostic already exists\n")
        elif not isinstance(diagnostic, str):
            print("\nDiagnostic variable must be a string\n")
        else:
            self.db.database["diagnostics"].insert_one({'diagnostic':diagnostic})

    def remove_diagnostic(self, diagnostic: str):
        """ Removes a diagnostic from the diagnostics collection.

        Parameters
        ----------
        diagnostic : str 
            The name of a valid diagnostic stored in the diagnostics collection.
        """
        if not self.query.diagnostic_exists(diagnostic):
            print("\nDiagnostic doesn't exist\n")
        elif not isinstance(diagnostic, str):
            print("\nDiagnostic variable must be a string\n")
        else:
            self.db.database["diagnostics"].delete_one({'diagnostic':diagnostic})


    # Shot collection
    # ---------------------------------------------------------------------------
    def iterate_shot_number(self):
        """ Adds one to the last_shot field in the run_setup collection. """
        shot_number = self.db.database["run_setup"].distinct("last_shot")[0]
        next_shot_number = shot_number + 1
        update_operation = {"$set": {"last_shot": next_shot_number}}
        self.db.database["run_setup"].update_one({}, update_operation)

    def reset_shot_count(self):
        """ Sets the last_shot field in the run_setup collection to zero. """
        update_operation = {"$set": {"last_shot": 0}}
        self.db.database["run_setup"].update_one({}, update_operation)


    # Experiment collection
    # ---------------------------------------------------------------------------
    def set_experiment(self, name: str):
        """ Sets the name of the experiment in the run_setup collection. Once set 
            this field can be queried from anywhere and archived within
            your metadata dictionary.
        """
        update_operation = {"$set": {"experiment": name}}
        self.db.database["run_setup"].update_one({}, update_operation)
    
    
    # Data collections 
    # ---------------------------------------------------------------------------
    def update_doc(self, update_dict: dict, value_filter_dict = {}, 
                         range_filter_dict = {}, command = 'replace'):
        """ General multifield update query.

        This function returns the documents corresponding to the value and filter 
        dictionaries and replaces the document field value according to the update 
        dictionary.
        IMPORTANT: this function can overwrite data.

        Parameters
        ----------
        update_dict : dict
        Example (replace & insert):
            update_dict = { 
                            'metadata' : { 'experiment' : 'EXP_TEST',
                                           'test_field': 'test_entry'
                                         },
                            'data' : { 'data_field' : <new entry>}
                          } 
        
        value_filter_dict : dict
        Example:
            value_query_dict = {
                                'metadata' : { 'experiment' : [<value 1>, <value 2>, ...],
                                               'diagnostic' : [<value 1>, <value 2>, ...],
                                               'instrument' : [<value 1>, <value 2>, ...],
                                               'other_data' : [<value 1>, <value 2>, ...]
                                             },
                                'data' : {'data_field' : [<data_value1>, <data_value2>]}
                               }
        
        range_filter_dict : dict
        Example:
            range_query_dict = {
                                'metadata' : {'shot_number' : [<lower bound>, <upper bound>]},
                                'data' : {'data_field' : [<lower_bound>, <upper_bound>}
                               }

        command: str, default: 'replace'
            replace: It will replace the value in the document with the value 
                     in the document(s) update dictionary where the fields match.

            insert:  It will add a new field, value pair to the document(s). If the 
                     field exists it will overwrite the current entry.

            append:  It will append the value found in the update dictionary to 
                     the document(s) dict/list value where the fields match. If 
                     field doesn't exist it will be created.
        """

        # Check if the command is valid
        # -------------------------------------------------------------
        command_list = ['replace', 'insert', 'append']
        if (command not in command_list):
            print(f'\nERROR in update_query, input: command -- invalid arguements, must be ' + \
                  f'one of these commands: {command_list}\n')
            exit()

        # Create the filter query
        # -------------------------------------------------------------
        # Create the query pipeline
        self.query.query_data_value(value_filter_dict)
        self.query.query_data_range(range_filter_dict)

        # Combine every match query in the filter pipeline
        filter_query = {'$and' : []}
        for match_filter in self.query.filter_pipeline: 
            filter_list = match_filter['$match']['$and']

            # Add each query under the '$and' operator in the filter
            for i in range(len(filter_list)):
                filter_query['$and'].append(filter_list[i])

        # Update the associated fields with the new information
        # -------------------------------------------------------------
        update_cnt, update_query = 0, {'$set' : {}, '$push' : {}}
        for dtype in update_dict.keys(): 
            
            # If there are multiple updates for a given data type [ data or metadata ]
            for field, entry in update_dict[dtype].items():

                # Add field value pairs to the update query, dependent on input command
                # ----------------------------------------------------
                field = f'{dtype}.{field}'
                
                if (command == 'append'):
                    # Return the structure of the data we are appending to
                    if ('append_to' not in update_dict[dtype].keys()):
                        print(f'\nERROR in append_query, missing append_to key value pair ' + \
                              f'from the data type subdictionary\n')
                        exit()
                    else:
                        # Check that the entry is valid
                        entry_type = update_dict[dtype]['append_to']
                        if (entry_type not in ['dict', 'list']):
                            print(f'\nERROR in append_query, invalid append_to structure, ' + \
                                  f'must be one of two strings: dict or list\n')
                            exit()

                    # Skip to next field since this value is known
                    if (field == 'metadata.append_to'): continue 

                    # Fill the appropriate query dictionary based on the entry type
                    if (entry_type == 'dict'):
                        for entry_field, entry_val in entry.items(): 
                            update_query['$set'].update({f'{field}.{entry_field}' : entry_val})
                        
                    if (entry_type == 'list'):     
                        update_query['$push'].update({field : entry})

                else: # replace or insert
                    update_query['$set'].update({field : entry})

                # If we aren't inserting make sure the document contains the fields requesting update
                if (command != 'insert'): filter_query['$and'].append({field : {'$exists' : True}})

        # Try the update over each collection
        # -------------------------------------------------------------
        for collection in self.query.collections:
            update_res = self.db.database[collection].update_many(filter_query, update_query)
            
            # If the update is successful exit loop
            if update_res.modified_count > 0:
                update_cnt += update_res.modified_count

        print(f'\n{update_cnt} document(s) updated.\n')
   

    def add_note_to_doc(self, shot_number: int, device_name: str, msg: str):
        """ Add a note to a single documents notes list. It also stores the time this
            note was created and who it was created by automatically.

        Parameters
        ----------
        shot_number : int 
        
        device_name : str

        msg : str
            The note content.
        """
        value_filter_dict = { 'metadata' : {'shot_number' : [shot_number]} }
        update_dict = { 'metadata' : { 'append_to' : 'list',
                                       'notes' : { 'created_by' : pwd.getpwuid(os.getuid()).pw_name, 
                                                   'date' : datetime.now(),
                                                   'content' : msg
                                                 }
                                     }
                      }

        self.update_doc(update_dict, value_filter_dict, {}, command = 'append')
