from datetime import datetime
from typing import Union
import asyncio

"""
Module used to store global discord app state
"""
guild_server_map_lock = asyncio.Lock()
guild_server_map: dict[int, Server] = {}

start_time: Union[datetime, None] = None
server_membership_count: int = 0
