"""
This module contains the AdminAPI class for database administration tasks.
"""

from .database  import Database
from .query_api import QueryAPI

class AdminAPI:
    def __init__(self, db: Database):
        self.db = db
        self.query = QueryAPI(self.db)

    # Instrument collection
    def add_instrument(self, instrument: str, gridfs_bool: bool):
        if self.query.instrument_exists(instrument):
            print("\nInstrument already exists\n")
        elif not isinstance(instrument, str):
            print("\nInstrument variable must be a string\n")
        elif not isinstance(gridfs_bool, bool):
            print("\nSecond input must be a boolean variable: True/False\n")
        else:
            self.db.database["instruments"].insert_one({'instrument':instrument, 'gridfs':gridfs_bool})

    def remove_instrument(self, instrument: str):
        if not self.query.instrument_exists(instrument):
            print("\nInstrument doesn't exists\n")
        elif not isinstance(instrument, str):
            print("\nInstrument variable must be a string\n")
        else:
            self.db.database["instruments"].delete_one({'instrument':instrument})


    # Diagnostic collection
    def add_diagnostic(self, diagnostic: str):
        if self.query.diagnostic_exists(diagnostic):
            print("\nDiagnostic already exists\n")
        elif not isinstance(diagnostic, str):
            print("\nDiagnostic variable must be a string\n")
        else:
            self.db.database["diagnostics"].insert_one({'diagnostic':diagnostic})

    def remove_diagnostic(self, diagnostic: str):
        if not self.query.diagnostic_exists(diagnostic):
            print("\nDiagnostic doesn't exists\n")
        elif not isinstance(diagnostic, str):
            print("\nDiagnostic variable must be a string\n")
        else:
            self.db.database["diagnostics"].delete_one({'diagnostic':diagnostic})


    # Shot collection
    def iterate_shot_number(self):
        shot_number = self.db.database["run_setup"].distinct("last_shot")[0]
        next_shot_number = shot_number + 1
        update_operation = {"$set": {"last_shot": next_shot_number}}
        self.db.database["run_setup"].update_one({}, update_operation)

    def reset_shot_count(self):
        update_operation = {"$set": {"last_shot": 0}}
        self.db.database["run_setup"].update_one({}, update_operation)


    # Experiment collection
    def set_experiment(self, name):
        update_operation = {"$set": {"experiment": name}}
        self.db.database["run_setup"].update_one({}, update_operation)

