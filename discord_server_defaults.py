from discord import Message

from discord_server import Server


async def info_command(msg: Message, srv: Server):
    pass


async def play_playlist_command(msg: Message, srv: Server, url_or_query: str = None):
    pass


def get_defaults(prefix: str):
    commands = [
        (fr"\{prefix}info|i.*", info_command),
        (fr"\{prefix}playlist|pl https:\/\/www\.youtube\.com|youtu\.be\/.*?list=([a-zA-Z0-9]+)\??.*", play_playlist_command)
    ]
