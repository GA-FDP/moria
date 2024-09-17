"""
This module contains the Database class which manages the connection to the database.
"""

import pymongo
from   pymongo import MongoClient
import gridfs

class Database:
    def __init__(self, db_name: str, server_ip = None):
        # connect to the database
        self.mongo_client = pymongo.MongoClient(server_ip)
        self.database = self.mongo_client[db_name]
        self.gridfs = gridfs.GridFS(self.database)
