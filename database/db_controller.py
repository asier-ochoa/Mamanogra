import database.schema as schema
import sqlite3
from os.path import isfile


class DB:
    def __init__(self):
        self.con: sqlite3.Connection = None
        self.cur: sqlite3.Cursor = None
        if not isfile('../savedata.db'):
            self.create_database()
        else:
            self.con = sqlite3.connect('../savedata.db')
            self.cur = self.con.cursor()

    def create_database(self):
        """
        Launches database queries to build all relevant tables
        """
        self.con = sqlite3.connect('../savedata.db')
        self.cur = self.con.cursor()
        self.cur.execute(schema.generate())