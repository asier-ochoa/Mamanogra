from datetime import datetime

from discord import Message, HTTPException, Forbidden
from config import config
import global_state

from discord_server import Server
from discord_server_commands import Command


async def info_command(msg: Message, srv: Server):
    try:
        await msg.channel.send(
            content="\n".join((
                "```",
                f"Mamanogra v0.13 - {config.discord.info_message}",
                "Made by Smug Twingo",
                f"Uptime: {str(datetime.now() - global_state.start_time).split('.')[0]}"
                "```"
            ))
        )
    # Make error messages more detailed
    except Forbidden as exc:
        print(f"Error: Insufficient permissions. Details: {exc.response}")
    except HTTPException as exc:
        print(f"Error: HTTPException while trying to write info message. Details: {exc.response}")


async def play_url_command(msg: Message, srv: Server, yt_id: str = None):
    pass


async def play_query_command(msg: Message, srv: Server, query: str = None):
    queries = query.split('|')
    if len(queries) == 1:
        print("Info: Single q")
    else:
        print("Info: Multiple q")
    pass


async def play_playlist_command(msg: Message, srv: Server, yt_id: str = None):
    pass


def get_defaults(prefix: str):
    commands = [
        (fr"\{prefix}(?:info|i)", info_command),
        (fr"\{prefix}(?:p|play) https:\/\/(?:(?:www\.youtube\.com\/.*?watch\?v=([\w\d]*).+)|(?:youtu\.be\/([\w\d]+)))", play_url_command),
        (fr"\{prefix}(?:p|play) ([^|]+(?:\|(?:[^|]+))*)", play_query_command),
        (fr"\{prefix}(?:pl|playlist) https:\/\/www.youtube.com\/.*?list=([\w\d]*).*", play_playlist_command)
    ]
    return [Command(*x) for x in commands]
