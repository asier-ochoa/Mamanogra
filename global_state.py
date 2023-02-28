"""
Module used to store global discord app state
"""
from datetime import datetime
from typing import Optional
from discord import Client
import asyncio

from discord_server import Server

guild_server_map_lock = asyncio.Lock()
guild_server_map: dict[int, Server] = {}

start_time: Optional[datetime] = None
server_membership_count: int = 0

discord_client: Optional[Client] = None
