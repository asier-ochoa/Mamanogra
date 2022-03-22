from discord import VoiceChannel, VoiceClient, FFmpegPCMAudio
from yt_dlp import YoutubeDL
from datetime import datetime
from threading import Lock
import time

class Player:
    """
    Player class gets instantiated when starting bot.
    """
    voice_client:VoiceClient = None
    connected_channel:VoiceChannel = None

    queue:list = None
    """
    The music queue is represented with a list containing tuples:
    - (<name>,<link>,<duration>)
    Optionally:
    - (<name>,<link>,<duration>,<seek>)
    """

    # This is a reference to a callback function in controller, called after a song ends
    callback = None

    # These should only be changed inside the class,dont want to make them private XDDDDDDDD
    is_playing = False # Represents if bot is currently connected and has a song in buffer (includes being paused)
    is_paused = False # For this to be true, is playin must also be true.
    song_end:datetime = None

    #yt_dlp client reference
    yt_client:YoutubeDL = None

    def __init__(self, callback, resumeQueue = None):
        """
        Passing a list to the bot with songs will instantiate
        a given song queue.
        """
        self.yt_client = YoutubeDL({'noplaylist':'True'})
        if resumeQueue is not None:
            self.queue = resumeQueue

        self.callback = callback
        self.queue = []
    
    async def connect_channel(self, caller_channel:VoiceChannel):
        """
        Connects to channel of calling message author.
        Voice channel must be passed to it, control relegated
        to controller.py
        """
        if self.connected_channel is None:
            try:
                self.connected_channel = await caller_channel.connect()
            except Exception as exc:
                pass #put message about lacking permissions
        else:
            pass #throw exception about already being connected

    def query_extract(self, query:str):
        info = self.yt_client.extract_info(f'ytsearch:{query}', download=False)
        return info['entries'][0]['id']

    def extract_info(self, url:str):
        info = self.yt_client.extract_info(url, download=False)

        #extract audio url
        ff_link = ''
        for format in info["formats"]:
            if format.get("format_id") == '251':
                ff_link = format["url"]
                break
        if ff_link == '':
            for format in info["formats"]:
                if format.get("format_id") == '140':
                    ff_link = format["url"]
                    break

        return (info['title'], ff_link, info['duration'])

    async def disconnect_channel(self):
        if self.voice_client is not None:
            await self.voice_client.disconnect()
            self.voice_client = None

    def start_playing(self, url_override=None):
        """
        Starts playing the first song on the queue. Returns a string with the title of the song.

        If a string is passed to the url_override parameter, a specific url can be played. (Not Implemented)
        """
        channel = self.connected_channel
        if channel is None:
            raise Exception("Bot not connected to any voice channel.")

        if len(self.queue) < 1:
            raise Exception("No song currently on queue.")

        if len(self.queue[0]) > 3:
            ffmpeg_params = f'-ss {self.queue[0][3].strftime("%H:%M:%S")}'
        else:
            ffmpeg_params = ''

        url = self.queue[0][1]
        self.connected_channel.play(FFmpegPCMAudio(url, before_options=ffmpeg_params), after=lambda error: self.end_playing_song(error))

    def end_playing_song(self, error):
        """
        Callback function for when a song ends playing.
        """
        # lock = Lock() # Could use these locks to guarantee safety
        # lock.acquire()
        self.queue.pop(0)
        # lock.release()
        self.callback()

    def pause(self):
        self.connected_channel.pause()
        pass

    def resume_playing(self):
        self.connected_channel.resume()
        pass

    def stop_playing(self):
        self.connected_channel.stop()

    def register_song(self, song, time = None):
        """
        Pushes song into queue list.
        You can optionally pass a time parameter to seek
        so it gets inserted as next song
        """
        if time is not None:
            song = (song[0],song[1],song[2], time)
            self.queue.insert(1, song)
        else:
            self.queue.append(song)