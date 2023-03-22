from datetime import datetime

from discord import Message, Forbidden, HTTPException

import global_state
from config import config
from bot.discord_server import Server
from bot.discord_server_commands import Command


async def info_command(msg: Message, srv: Server):
    try:
        await msg.channel.send(
            content="\n".join((
                "```",
                f"Mamanogra v0.2 - {config.discord.info_message}",
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


async def webui_command(msg: Message, srv: Server):
    try:
        await srv.generate_web_key(msg.author)
    except Forbidden as exc:
        print(f"Error: Couldn't send key registration url to {msg.author.name}#{msg.author.discriminator}. Details: {exc.response}")
        await msg.channel.send(f"{msg.author.mention}\n```\nCouldn't send the webui URL through your DM. Check your privacy settings and try again.\n```")


def get_global_defaults(prefix: str):
    commands = [
        (fr"\{prefix}(?:info$|i$)", info_command),
        (fr"\{prefix}(?:w$|webui$)", webui_command)
    ]
    return [Command(*x) for x in commands]
