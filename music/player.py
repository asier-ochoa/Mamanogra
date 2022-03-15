from discord import VoiceChannel, VoiceClient, FFmpegPCMAudio
from yt_dlp import YoutubeDL
from datetime import datetime

class Player:
    """
    Player class gets instantiated when starting bot.
    """
    voice_client:VoiceClient = None
    connected_channel:VoiceChannel = None

    queue:list = []
    """
    The music queue is represented with a list containing tuples:
    - (<name>,<link>,<duration>)
    """

    is_playing = False
    song_end:datetime = None

    #yt_dlp client reference
    yt_client:YoutubeDL = None
    
    def __init__(self, resumeQueue = None):
        """
        Passing a list to the bot with songs will instantiate
        a given song queue.
        """
        self.yt_client = YoutubeDL()
        if resumeQueue is not None:
            self.queue = resumeQueue
    
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

        url = self.queue[0][1]
        self.connected_channel.play(FFmpegPCMAudio(url))

    def pause(self):
        self.connected_channel.pause()
        pass

    def resume_playing(self):
        self.connected_channel.resume()
        pass

    def register_song(self, song):
        """
        Pushes song into queue list.
        """
        self.queue.append(song)


    def skip_playing(self):
        """
        Returns a message to be sent to text channel
        """
        pass