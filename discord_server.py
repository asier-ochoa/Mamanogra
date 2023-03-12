import os
import re
from datetime import datetime
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
        key = "".join(hex(x).removeprefix('0x') for x in os.urandom(128))
        token = "".join(hex(x).removeprefix('0x') for x in os.urandom(16))
        with database:
            status = database.get_web_keys_status(user.id)
            # If no key or token, generate a new one
            if status is None:
                database.register_new_web_key(user.id, key, token)
                await user.send(f"Your URL:\n{config.server.domain}:{config.server.port}/keygen/{token}\nExpires in 5 minutes")
                print(f"Info: Generated token ({token}) and key for {user.name}#{user.discriminator} in {self.disc_guild.name}")
                return
            # If token but no key, resend
            if status.request_token_expiration_date > datetime.now() and not status.validated:
                await user.send(f"Resending URL:\n{config.server.domain}:{config.server.port}/keygen/{status.request_token}\nExpires soon")
                print(f"Info: Resent token url for {user.name}#{user.discriminator} in {self.disc_guild.name}")
                return
            # If token expired and still no key, regenerate
            if status.request_token_expiration_date < datetime.now() and not status.validated:
                database.regenerate_token(status.id, token)
                await user.send(f"Regenerating URL:\n{config.server.domain}:{config.server.port}/keygen/{token}\nExpires in 5 minutes")
                print(f"Info: Regenerated token ({token}) for {user.name}#{user.discriminator} in {self.disc_guild.name}")
                return
            # Has key, regenerate
            if status.key_expiration_date < datetime.now() or status.validated:
                database.regenerate_key(status.id, key)
                database.regenerate_token(status.id, token)
                await user.send(f"Your URL:\n{config.server.domain}:{config.server.port}/keygen/{token}\nExpires in 5 minutes")
                print(f"Info: Regenerated token ({token}) and key for {user.name}#{user.discriminator} in {self.disc_guild.name}")
                return


def register_command(server: Server, regex: str, delegate: Callable[[Message, Server], Awaitable[Any]]):
    server.commands.append(Command(regex, delegate))
    return server  # Allow method chaining
