from typing import Iterable, Union, Optional

from pydantic import BaseModel

import database.schema as schema
from music.player import Song
import sqlite3
from os.path import isfile
from datetime import datetime, timedelta
from threading import Lock


class WebKeyStatus(BaseModel):
    id: int
    key_expiration_date: datetime
    request_token: str
    request_token_expiration_date: datetime
    validated: bool
    key: Optional[str]


class DB:
    db_file_name = 'savedata.db'

    def __enter__(self):
        self.lock.acquire()
        self.con = sqlite3.connect(self.db_file_name)
        self.cur = self.con.cursor()
        return self

    def __exit__(self, exception_type, exception_value, tb):
        self.con.commit()
        self.con.close()
        self.con = None
        self.cur = None
        self.lock.release()

    def __init__(self):
        self.con: Union[sqlite3.Connection, None] = None
        self.cur: Union[sqlite3.Cursor, None] = None
        self.lock = Lock()
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
            , [server_fk, user_fk, datetime.now().isoformat(), song.yt_id, song.name, song.duration]
        )
        return self.cur.lastrowid

    def log_command(self, command: str, user_discord_id: int, server_discord_id: int):
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
            INSERT INTO command_log (server, writer, command, date_issued) values (?, ?, ?, ?)
            """
            , [server_fk, user_fk, command, datetime.now().isoformat()]
        )

    def get_top_songs_local(self, user_discord_id: int, server_discord_id: int, amount=10):
        assert self.con is not None and self.cur is not None

        amount = amount if amount < 1000 else 10
        user_fk, server_fk = self.cur.execute(
            """
            SELECT u.id, s.id from user_membership 
            join servers s on s.id = user_membership.server_id
            join users u on u.id = user_membership.user_id
            where u.discord_id = ? and s.discord_id = ? limit 1
            """
            , [str(user_discord_id), str(server_discord_id)]
        ).fetchone()

        return self.cur.execute(
            """
            SELECT songs.video_name, songs.video_id, count(video_id) from songs
                join users u on u.id = songs.requestee
                join servers s on s.id = songs.server
                where u.id = ? and s.id = ?
                group by video_id
                order by count(video_id) desc
                limit ?
            """
            , [user_fk, server_fk, amount]
        )

    def get_top_songs_global(self, user_discord_id: int, amount=10):
        assert self.con is not None and self.cur is not None

        amount = amount if amount < 1000 else 10
        user_fk = self.cur.execute(
            """
            SELECT id from users
            where discord_id = ? limit 1
            """
            , [str(user_discord_id)]
        ).fetchone()[0]

        return self.cur.execute(
            """
            SELECT songs.video_name, songs.video_id, count(video_id) from songs
                join users u on u.id = songs.requestee
                where u.id = ?
                group by video_id
                order by count(video_id) desc
                limit ?
            """
            , [user_fk, amount]
        )

    def get_top_songs_server(self, server_discord_id: int, amount=10):
        assert self.con is not None and self.cur is not None

        amount = amount if amount < 1000 else 10
        server_fk = self.cur.execute(
            """
            SELECT id from servers
            where discord_id = ? limit 1
            """
            , [str(server_discord_id)]
        ).fetchone()[0]

        return self.cur.execute(
            """
            select songs.video_name, songs.video_id, count(video_id) from songs
                join servers s on s.id = songs.server
                where s.id = ?
                group by video_id
                order by count(video_id) desc
                limit ?
            """
            , [server_fk, amount]
        )

    def get_all_user_servers(self, usr_db_id: int) -> list[int]:
        assert self.con is not None and self.cur is not None

        return [
            int(x[0]) for x in
            self.cur.execute(
                """
                SELECT s.discord_id from user_membership
                join servers s on s.id = user_membership.server_id
                where user_id = ?
                """, [usr_db_id]
            ).fetchall()
        ]

    def register_song_listeners(self, db_song_id: int, user_ids: tuple[int]):
        assert self.con is not None and self.cur is not None

        user_ids = [
            (r[0], db_song_id) for r in
            self.cur.execute(
                """
                SELECT id from users
                WHERE discord_id in (
                """ + ",".join(["?"] * len(user_ids)) + ")",
                user_ids
            ).fetchall()
        ]

        self.cur.executemany(
            """
            INSERT INTO song_listener (listener_user, song)
            VALUES (?, ?)
            """, user_ids
        )

    def register_new_web_key(self, user_id: int, key: str, token: str):
        """
        Returns false if no data was inserted
        """
        assert self.con is not None and self.cur is not None

        user_fk = self.cur.execute(
            """
            SELECT id from users
            where discord_id = ? limit 1
            """, [user_id]
        ).fetchone()[0]

        token_exp_date = datetime.now() + timedelta(minutes=5)
        key_exp_date = datetime.now() + timedelta(days=90)
        self.cur.execute(
            """
            INSERT into webui_session_keys (discord_user, key, key_expiration_date, request_token, request_token_expiration_date, key_validated)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (user_fk, key, key_exp_date, token, token_exp_date, 0)
        )
        return True

    def get_web_keys_status(self, user_id: int) -> Optional[WebKeyStatus]:
        assert self.con is not None and self.cur is not None

        user_fk = self.cur.execute(
            """
            SELECT id from users
            where discord_id = ? limit 1
            """, [user_id]
        ).fetchone()[0]

        status = self.cur.execute(
            """
            SELECT id, key_expiration_date, request_token, request_token_expiration_date, key_validated from webui_session_keys
            WHERE discord_user = ? limit 1
            """, [user_fk]
        ).fetchone()
        if status is None:
            return None
        return WebKeyStatus(
            id=status[0],
            key_expiration_date=status[1],
            request_token=status[2],
            request_token_expiration_date=status[3],
            validated=status[4]
        )

    def regenerate_token(self, db_key_id: int, token: int):
        assert self.con is not None and self.cur is not None

        token_exp_date = datetime.now() + timedelta(minutes=5)
        self.cur.execute(
            """
            UPDATE webui_session_keys SET 
            request_token = ?,
            request_token_expiration_date = ?
            WHERE id = ?
            """, (token, token_exp_date, db_key_id)
        )

    def regenerate_key(self, db_key_id: int, key: str):
        assert self.con is not None and self.cur is not None

        key_exp_date = datetime.now() + timedelta(days=90)
        self.cur.execute(
            """
            UPDATE webui_session_keys SET
            key = ?,
            key_validated = ?,
            key_expiration_date = ? 
            WHERE id = ?
            """, (key, 0, key_exp_date, db_key_id)
        )

    def get_web_key_with_token(self, token: str):
        assert self.con is not None and self.cur is not None

        status = self.cur.execute(
            """
            SELECT id, key_expiration_date, request_token, request_token_expiration_date, key_validated, key from webui_session_keys
            WHERE request_token = ? limit 1
            """, [token]
        ).fetchone()
        if status is None:
            return None
        return WebKeyStatus(
            id=status[0],
            key_expiration_date=status[1],
            request_token=status[2],
            request_token_expiration_date=status[3],
            validated=status[4],
            key=status[5]
        )

    def validate_key(self, db_id: int):
        assert self.con is not None and self.cur is not None

        self.cur.execute(
            """
            UPDATE webui_session_keys SET
            key_validated = ?
            WHERE id = ?
            """, (1, db_id)
        )

    def auth_key(self, key: str) -> tuple[bool, Optional[WebKeyStatus]]:
        """
        Used to authenticate with key, checks for validity
        """
        assert self.con is not None and self.cur is not None

        search = self.cur.execute(
            """
            SELECT id, key_expiration_date, request_token, request_token_expiration_date, key_validated from webui_session_keys
            where key = ? limit 1
            """, [key]
        ).fetchone()

        if search is None:
            return False, None
        if not bool(search[4]):
            return False, None
        if datetime.fromisoformat(search[3]) < datetime.now():
            return False, None
        return True, WebKeyStatus(
            id=search[0],
            key_expiration_date=search[1],
            request_token=search[2],
            request_token_expiration_date=search[3],
            validated=search[4],
            key=None
        )



database = DB()
