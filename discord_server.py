import os
import re
from typing import Callable, Any, Awaitable, Iterable

from discord import Guild, Message, VoiceState, User

from config import config
from db_controller import database
from discord_server_commands import Command
from music_player import MusicPlayer


class Server:
    """
    Used to internally represent a discord guild
    Contains commands, music queue
    """
    def __init__(self, guild: Guild):
        self.disc_guild = guild
        self.commands: list[Command] = []  # Match command using regex, delegate argument parsing to function
        self.music_player = MusicPlayer(self.disc_guild)

    async def message_entrypoint(self, message: Message):
        try:
            # Match command regex and send to delegate, calls first match
            # Send matched groups as arguments to delegate
            for c in self.commands:
                match = re.fullmatch(c.regex, message.content)
                if match:
                    with database:
                        database.log_command(message.content, message.author.id, self.disc_guild.id)
                    await c.delegate(message, self, *[x for x in match.groups() if x is not None])
                    return
        except Exception as exc:
            self.message_error_handler(message, exc)

    async def voice_state_entrypoint(self, before: VoiceState, after: VoiceState):
        if before.channel is not None and after.channel is None and not self.music_player.disconnect_flag:
            print(f"Info: Bot forcefully disconnected from {before.channel.name}")
            self.music_player.force_disconnect_flag = True
            await self.music_player.voice_client.disconnect(force=True)
            self.music_player.voice_client = None
        if self.music_player.disconnect_flag:
            self.music_player.disconnect_flag = False

    def register_commands(self, command: Iterable[Command]):
        self.commands.extend(command)

    async def generate_web_key(self, user: User):
        key = os.urandom(128)
        token = "".join(hex(x).removeprefix('0x') for x in os.urandom(16))
        with database:
            if not database.register_new_web_key(user.id, key, token):
                if not database.regen_web_key(user.id, key, token):
                    await user.send(f"Your URL is still active, if you wish to regen your URL use command `+wr` in a server")
        await user.send(f"Your URL:\n```\na.smugtwingo.xyz:{config.server.port}/keygen/{token}\n```Expires in 5 minutes")
        print(f"Info: Generated token ({token}) and key for {user.name}#{user.discriminator} in {self.disc_guild.name}")


def register_command(server: Server, regex: str, delegate: Callable[[Message, Server], Awaitable[Any]]):
    server.commands.append(Command(regex, delegate))
    return server  # Allow method chaining
