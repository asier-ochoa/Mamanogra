import asyncio
from copy import deepcopy
from datetime import datetime, time, timedelta
from enum import Enum
from functools import wraps
from typing import Union, Callable, Optional, Any

from discord import FFmpegPCMAudio, Guild, User, Member, VoiceClient, ClientException, VoiceChannel
from yt_dlp import YoutubeDL

import global_state

FFMPEG_YT_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}


class RepeatType(Enum):
    N_TIMES = 0
    ONCE = 1
    FOREVER = 2


class Song:
    """
    POD-like class to gather song data
    """
    def __init__(self, source_func: Callable[[], FFmpegPCMAudio], requester: Member):
        self.source_func = source_func
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

    # Returns a function with bound variables to serve as callback
    def finishing_callback(self):
        def callback(error: Optional[Exception], player: MusicPlayer = self):
            if error is not None:
                print(f"Error: Exception received while playing a song. Details: {error}")
                return
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
        return callback

    async def play(self, caller: Union[Member, User], source_func: Optional[Callable[[], FFmpegPCMAudio]] = None):
        # Connect to a voice channel if not connected
        await self.connect_to_channel(caller.voice.channel)

        async with self.voice_client_lock:
            # Append a song if passed as argument
            if source_func is not None:
                self.queue.append(Song(source_func, caller))
        if not self.voice_client.is_playing():
            self.queue[self.current_index].time_played = datetime.now()
            played_ago = self.queue[self.current_index].time_played - self.queue[self.current_index].time_requested
            print("".join([
                f"Info: playing song requested by {caller.name}#{caller.discriminator}",
                f" {played_ago.__str__()} ago"
            ]))
            self.voice_client.play(self.queue[self.current_index].source_func(), after=self.finishing_callback())

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


# Use factory pattern to embed different types of playable audio as a function
def generate_youtube_song(yt_id: str, seek: Optional[int] = None) -> Callable[[], FFmpegPCMAudio]:
    def youtube_song(i_yt_id=yt_id, i_seek=seek):  # Default params for early binding
        ffmpeg_options = deepcopy(FFMPEG_YT_OPTIONS)
        # Add seeking if requested
        if i_seek is not None:
            seek_time = timedelta(seconds=i_seek)
            ffmpeg_options['before_options'] += ''.join([
                ' -ss ',
                f'{seek_time.seconds // 3600}:',
                f'{seek_time.seconds // 60 % 60}:',
                f'{seek_time.seconds % 60}'
            ])

        yt_query = YoutubeDL(
            {'format': 'bestaudio/best', 'quiet': True, 'noplaylist': True}
        ).extract_info(i_yt_id, download=False)
        if i_yt_id.startswith("ytsearch:"):
            yt_query = yt_query['entries'][0]
        audio_format: str = yt_query['format_id']
        audio_url = [
            x for x in yt_query['formats']
            if x['format_id'] == audio_format
        ][0]['url']

        return FFmpegPCMAudio(source=audio_url, **ffmpeg_options)
    return youtube_song





