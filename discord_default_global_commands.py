from datetime import datetime

from discord import Message, Forbidden, HTTPException

import global_state
from config import config
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


def get_global_defaults(prefix: str):
    commands = [
        (fr"\{prefix}(?:info$|i$)", info_command)
    ]
    return [Command(*x) for x in commands]
