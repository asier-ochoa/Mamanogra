from typing import Iterable

import database.schema as schema
import sqlite3
from os.path import isfile
from os import remove


class DB:
    db_file_name = 'savedata.db'

    def __enter__(self):
        self.con = sqlite3.connect(self.db_file_name)
        self.cur = self.con.cursor()
        return self

    def __exit__(self, exception_type, exception_value, tb):
        self.con.commit()
        self.con.close()
        self.con = None
        self.cur = None

    def __init__(self):
        self.con: sqlite3.Connection | None = None
        self.cur: sqlite3.Cursor | None = None
        if not isfile(self.db_file_name):
            self.create_database()

    def create_database(self):
        """
        Launches database queries to build all relevant tables
        """
        with self as d:
            d.cur = self.con.cursor()
            d.cur.executescript(schema.generate())

    def register_server_and_members(self, server_id: int, owner_id: int):
        # Verifiy connection to database
        assert self.con is not None and self.cur is not None

        owner_exists = self.cur.execute(
            """
            SELECT EXISTS(
                SELECT 1 FROM users where discord_id=?
            )
            """
            , (str(owner_id))
        )
        self.cur.execute(
            """
            INSERT OR IGNORE INTO servers (discord_id, name, owner) VALUES (?,?,?)
            """
            , (server_id, owner_id)
        )

    def register_users(self, users: Iterable[tuple[int, str]]):
        assert self.con is not None and self.cur is not None

        users = [(str(x[0]), x[1]) for x in users]
        self.cur.executemany(
            """
            INSERT INTO users (discord_id, name) values (?,?)
            """
            , users
        )


if __name__ == "__main__":  # testing
    # if isfile('savedata.db'):
    #     remove('savedata.db')

    db = DB()
    with db:
        db.register_users([(37289172, "smug_twingo")])
