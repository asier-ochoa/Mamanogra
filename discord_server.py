import re
from typing import Callable, Any, Awaitable, Iterable

from discord import Guild, Message, VoiceState
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
                    await c.delegate(message, self, *[x for x in match.groups() if x is not None])
                    return
        except Exception as exc:
            self.message_error_handler(message, exc)

    async def voice_state_entrypoint(self, before: VoiceState, after: VoiceState):
        if before.channel is not None and after.channel is None:
            print(f"Info: Bot forcefully disconnected from {before.channel.name}")
            self.music_player.voice_client = None

    def register_commands(self, command: Iterable[Command]):
        self.commands.extend(command)


def register_command(server: Server, regex: str, delegate: Callable[[Message, Server], Awaitable[Any]]):
    server.commands.append(Command(regex, delegate))
    return server  # Allow method chaining
