"""
This module contains the Database class which manages the connection to the database.
"""

import pymongo
from   pymongo import MongoClient
import gridfs

class Database:
    """ Mongo database initialization.

    Initializes a connection to a live MongoDB service. Allowing querying and 
    archiving.

    Parameters
    ----------
    db_name : str
        The name of the database on the corresponding server.

    server_ip : str, default=None
        The IP address of the server that the data is stored on.
    """
    def __init__(self, db_name: str, server_ip = None):
        # connect to the database
        self.mongo_client = pymongo.MongoClient(server_ip)
        self.database = self.mongo_client[db_name]
        self.gridfs = gridfs.GridFS(self.database)
