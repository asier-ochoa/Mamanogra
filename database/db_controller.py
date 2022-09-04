from typing import Iterable

import database.schema as schema
from music.player import Song
import sqlite3
from os.path import isfile
from datetime import datetime
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

    def register_server(self, server_id: int, server_name: str, owner_id: int):
        # Verifiy connection to database
        assert self.con is not None and self.cur is not None

        owner_search = self.cur.execute(
            """
            SELECT * FROM users where discord_id = ?
            """
            , [str(owner_id)]
        )
        if owner_search.arraysize < 1:
            raise Exception(f"owner_id: {owner_id} not found in users table!")
        owner_fk = owner_search.fetchone()[0]

        self.cur.execute(
            """
            INSERT OR IGNORE INTO servers (discord_id, name, owner) VALUES (?,?,?)
            """
            , (server_id, server_name, owner_fk)
        )

    def register_users(self, users: Iterable[tuple[int, str]]):
        assert self.con is not None and self.cur is not None

        users = [(str(x[0]), x[1]) for x in users]
        self.cur.executemany(
            """
            INSERT OR IGNORE INTO users (discord_id, name) values (?,?)
            """
            , users
        )

    def register_memberships(self, server_id: int, users: Iterable[int]):
        assert self.con is not None and self.cur is not None

        server_fk = self.cur.execute(
            """
            SELECT id FROM servers where discord_id = ?
            """
            , [str(server_id)]
        ).fetchone()[0]
        users = [[str(u)] for u in users]
        users_fk = []
        for u in users:
            users_fk.append(self.cur.execute(
                """
                SELECT id FROM users where discord_id in (?)
                """
                , u
            ).fetchone()[0])

        users_fk = [(server_fk, u, 'Default') for u in users_fk]
        self.cur.executemany(
            """
            INSERT OR IGNORE INTO user_membership (server_id, user_id, perm_level) VALUES (?, ?, ?)
            """
            , users_fk
        )

    def register_song(self, song: Song, user_discord_id: int, server_discord_id: int):
        assert self.con is not None and self.cur is not None

        user_fk, server_fk = self.cur.execute(
            """
            SELECT u.id, s.id from user_membership 
            join servers s on s.id = user_membership.server_id
            join users u on u.id = user_membership.user_id
            where u.discord_id = ? and s.discord_id = ? limit 1
            """
            , [str(user_discord_id), str(server_discord_id)]
        ).fetchone()

        self.cur.execute(
            """
            INSERT INTO songs (server, requestee, date_requested, video_id, video_name, video_len) 
            VALUES (?, ?, ?, ?, ?, ?)
            """
            , [server_fk, user_fk, datetime.now(), song.yt_id, song.name, song.duration]
        )


database = DB()

