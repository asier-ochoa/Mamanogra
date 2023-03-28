import asyncio
from datetime import datetime
from enum import Enum
from typing import Union, Callable, Optional
from database.db_controller import database

from discord import FFmpegPCMAudio, Guild, User, Member, VoiceClient, ClientException, VoiceChannel

import global_state
import utils


class RepeatType(Enum):
    N_TIMES = 0
    ONCE = 1
    FOREVER = 2


class Song:
    """
    POD-like class to gather song data

    source_func must have these arguments with a default value in order to provide data about the song:
        - title: str
        - duration: int <seconds>
        - thumbnail: str <url to image>
    """
    def __init__(self, source_func: Callable[[], FFmpegPCMAudio], requester: Member):
        self.source_func = source_func  # Replace by an interface to a class instead of function
        self.requester = requester
        self.time_requested: datetime = datetime.now()
        self.time_played: Union[datetime, None] = None
        self.repeat_type: RepeatType = RepeatType.ONCE


class MusicPlayer:
    def __init__(self, guild: Guild):
        self.guild: Guild = guild  # Get voice client instance from here
        self.voice_client: Union[VoiceClient, None] = None
        self.voice_client_lock: asyncio.Lock = asyncio.Lock()
        self.queue: list[Song] = []
        self.current_index: int = 0  # Represents current song queue index

        self.seek_flag = False
        self.disconnect_flag = False
        self.force_disconnect_flag = False

        self.cleanup_task = global_state.discord_client.loop.create_task(
            self.cleanup_coro(120)
        )

    # Returns a function with bound variables to serve as callback
    def finishing_callback(self):
        def callback(error: Optional[Exception], last_song: Optional[Song] = self.queue[self.current_index] if self.current_index < len(self.queue) else None, player: MusicPlayer = self):
            if error is not None:
                print(f"Error: Exception received while playing a song. Details: {error}")
                return

            # Remove any seeking left over
            if last_song is not None:
                args = utils.get_function_default_args(last_song.source_func)
                if not player.seek_flag and 'seek' in args:
                    args['seek'] = None
                    last_song.source_func.__defaults__ = tuple(args.values())
                else:
                    player.seek_flag = False

            if not player.force_disconnect_flag and not player.disconnect_flag:
                player.current_index += 1
                if player.voice_client is not None:
                    if len(player.voice_client.channel.members) > 1:
                        # Play next song in the queue
                        if player.current_index < len(player.queue):
                            global_state.discord_client.loop.create_task(
                                player.play(
                                    player.queue[player.current_index].requester
                                )
                            )
            else:
                player.force_disconnect_flag = False
        return callback

    def print_queue(self) -> list[str]:
        ret, now = [], datetime.now()
        duration_integrity = True  # Turns false if any of the songs doesn't have duration
        summed_duration = 0
        for i, s in enumerate(self.queue):
            args = utils.get_function_default_args(s.source_func)
            ret.append(
                "".join([
                    f"{i - self.current_index}: {args.get('title', '<No Title>')[:40]}",
                    "" if len(args.get('title', '<No Title>')) < 40 else "...",
                    f" - {((now - s.time_played).seconds + (args['seek'] if args.get('seek') is not None else 0)) // 60:02}:{((now - s.time_played).seconds + (args['seek'] if args.get('seek') is not None else 0)) % 60:02}/" if 'duration' in args and i == self.current_index else " - ",
                    f"{args['duration'] // 60:02}:{args['duration'] % 60:02}"
                    if 'duration' in args else
                    "<No Duration>",
                    f" -> (est. {summed_duration // 60:02}:{summed_duration % 60:02})"
                    if duration_integrity and 'duration' in args and i > self.current_index else
                    f" -> (est. N/A)" if i > self.current_index else "",
                    " ---Playing---" if i == self.current_index else ""
                ])
            )
            if 'duration' not in args and i >= self.current_index:
                duration_integrity = False
            if duration_integrity and i > self.current_index:
                summed_duration += args['duration']
            if duration_integrity and i == self.current_index:
                summed_duration += (args['duration'] - (now - s.time_played).seconds - (args['seek'] if args.get('seek') is not None else 0))

        return ret

    async def play(self, caller: Union[Member, User], source_func: Optional[Callable[[], FFmpegPCMAudio]] = None, voice_channel: Optional[VoiceChannel] = None):
        # Connect to a voice channel if not connected
        await self.connect_to_channel(caller.voice.channel if voice_channel is None else voice_channel)

        async with self.voice_client_lock:
            # Append a song if passed as argument
            if source_func is not None:
                self.queue.append(Song(source_func, caller))
        if not self.voice_client.is_playing():
            song = self.queue[self.current_index]
            song_args = utils.get_function_default_args(song.source_func)

            self.voice_client.play(song.source_func(), after=self.finishing_callback())
            song.time_played = datetime.now()
            requested_ago = song.time_played - song.time_requested
            if song_args.get('seek') is None:
                await self.register_current_song_to_database()

            print("".join([
                f"Info: playing \"{song_args.get('title')}\" requested",
                f" by {caller.name}#{caller.discriminator} in {caller.guild.name}",
                f" {requested_ago.__str__().split('.')[0]} ago"
            ]))

    async def connect_to_channel(self, channel: VoiceChannel):
        async with self.voice_client_lock:
            if self.voice_client is None:
                print(f"Info: Attempting to connect to {channel.name} in {channel.guild.name}")
                try:
                    self.voice_client: VoiceClient = await channel.connect()
                except ClientException:
                    print(f"Error: Already connected to channel {channel.name} in {self.guild.name}. Syncing state")
                    await self.guild.voice_client.disconnect(force=True)
                    self.voice_client: VoiceClient = await channel.connect()

    async def register_current_song_to_database(self):
        cur_song = self.queue[self.current_index]

        class MockSong:
            def __init__(self, yt_id, name, duration):
                self.yt_id = yt_id
                self.name = name
                self.duration = duration

        args = utils.get_function_default_args(cur_song.source_func)
        if 'i_yt_id' in args:
            with database:
                database.register_song_listeners(
                    database.register_song(
                        MockSong(
                            args['db_youtube_id'],
                            args['title'],
                            args['duration']
                        ), cur_song.requester.id, self.guild.id
                    ),
                    [u.id for u in self.voice_client.channel.members]
                )

    async def cleanup_coro(self, interval: int):
        while True:
            await asyncio.sleep(interval)

            # Cleanup song queue
            if self.current_index > 4:
                async with self.voice_client_lock:
                    self.queue = self.queue[self.current_index - 4:]
                    last_index = self.current_index
                    self.current_index = 4
                print(f"Cleanup Info: Removed {last_index - self.current_index} songs from {self.guild.name}'s queue")

            # Cleanup by disconnecting if no one in channel or bot is not playing music
            if self.voice_client is not None and (len(self.voice_client.channel.members) <= 1 or not self.voice_client.is_playing()):
                channel_name: str = self.voice_client.channel.name
                async with self.voice_client_lock:
                    self.disconnect_flag = True

                    # Have to do this hacky shit since for some godforsaken reason
                    # calling disconnect doesn't trigger the finishing callback.
                    # This is fucking stupid.
                    self.finishing_callback()(None)
                    await self.voice_client.disconnect()

                    self.current_index = len(self.queue)
                    self.voice_client: Optional[VoiceClient] = None
                print(f"Cleanup Info: Disconnected voice client from \"{channel_name}\" in {self.guild.name}")
