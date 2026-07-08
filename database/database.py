"""
This module contains the Database class which manages the connection to the database.
"""

import os
import pymongo
from   pymongo import MongoClient
from   pymongo.errors import OperationFailure
import gridfs

class Database:
    """ Mongo database initialization.

    Initializes a connection to a live MongoDB service. Allowing querying and 
    archiving.

    Parameters
    ----------
    db_name : str
        The name of the database on the corresponding server.

    server_ip : str, default='localhost'
        The IP address of the server that the data is stored on.
    
    user_type : str, default='read' 
        Options: 'read', 'read_write', 'admin'
    """
    def __init__(self, db_name: str, server_ip: str = 'localhost', user_type: str = 'read'):
        self.db_name = db_name

        # Choose the credentials
        if (user_type == 'admin'):
            self.user_type = user_type
            username = os.getenv("MONGO_ADMIN_USER")
            password = os.getenv("MONGO_ADMIN_PASS")
        elif (user_type == 'read_write'):
            self.user_type = user_type
            username = os.getenv("MONGO_RW_USER")
            password = os.getenv("MONGO_RW_PASS")
        else:
            self.user_type = 'read'
            username = os.getenv("MONGO_READONLY_USER")
            password = os.getenv("MONGO_READONLY_PASS")

        # Build URI — with or without auth
        if username and password:
            authentication_db = 'admin'
            uri = (
                f"mongodb://{username}:{password}@{server_ip}:27017/"
                f"{db_name}?authSource={authentication_db}"
            )
        else:
            uri = f"mongodb://{server_ip}:27017/{db_name}"
        
        # Connect to the database
        self.mongo_client = MongoClient(uri)
        self.database = self.mongo_client[db_name]
        self.gridfs = gridfs.GridFS(self.database)
        self._verify_connection()

    def _verify_connection(self):
        try:
            self.mongo_client.admin.command("ping")
        except OperationFailure as e:
            raise ConnectionError(f"MongoDB authentication failed: {e}")
