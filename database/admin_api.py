"""
This module contains the AdminAPI class for database administration tasks.
"""

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
    def set_experiment(self, name: str):
        """ Sets the name of the experiment in the run_setup collection. Once set 
            this field can be queried from anywhere and archived within
            your metadata dictionary.
        """
        update_operation = {"$set": {"experiment": name}}
        self.db.database["run_setup"].update_one({}, update_operation)
