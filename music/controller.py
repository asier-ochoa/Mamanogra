import os
from io import TextIOWrapper
import json
import datetime
import re

import globals
from music.player import Player
from exceptions import InvalidArgumentFormat

from discord.guild import Guild
from discord.member import Member
from discord.user import User

class Controller:

    config:dict = None
    music_player:Player = None

    # list containing lambdas refering to functions, used to ensure programs execute one after the other
    cmd_queue:list = None
    
    def __init__(self, guild:Guild=None):
        if guild is None:
            raise TypeError('Guild cannot be none!')
            return None

        self.cmd_queue = []
        self.config = {}
        
        self.guild = guild
        guild_name = guild.name
        config_path = globals.SERVER_FOLDER + '/' + guild.name + '/' + 'music.json'

        self.music_player = Player(self.after_song) #instantiates the music client

        #default config template
        configData = {
            "users": {}, #inside values must be "username":"blacklist | whitelist | admin | owner"
            "prefixOverride" : None,
            "forceTextChannel" : None, #force bot to only answer and reply in said channel
            "forceVoiceChannel" : None, #force bot to only play in certain void channel
            "whitelist" : False, #boolean to only allow whitelisted users call commands
            "playlists":{}
        }

        if not os.path.exists(config_path):
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            f = open(config_path, 'w')
            f.write(json.dumps(configData,indent=3))
            f.close()
        
        #loads current config
        f = open(config_path)
        fstr:str = ''
        for line in f:
            fstr = fstr + line
        f.close()
        self.config = json.loads(fstr)

    async def check_user_privilege(self, user:User, elevated=False) -> bool:
        """
        Check if a certain user is allowed to execute music commands.
        Takes in a discord.User object.

        Pass elevated=True for admin commands
        """
        privilege = self.config['users'].get(user.name)
        is_whitelist = self.config['whitelist']

        if not elevated:
            if is_whitelist:
                if privilege in ('whitelist','admin','owner'):
                    return True
            else:
                if privilege != 'blacklist':
                    return True
        else:
            if privilege in ('admin','owner'):
                return True

        return False

    def after_song(self):
        """
        Gets called after a song ends playing
        """
        if len(self.music_player.queue) > 0:
            self.music_player.start_playing()

    async def play_url(self, url, caller:Member):
        song:tuple(str, str, int) = self.music_player.extract_info(url)
        self.music_player.register_song(song)

        # Avoid connecting if already connected
        if self.music_player.connected_channel == None:
            try:
                await self.music_player.connect_channel(caller.voice.channel)
            except Exception as e:
                pass #do something

        if not self.music_player.connected_channel.is_playing():
            self.music_player.start_playing()

    async def pause(self):
        if self.music_player.connected_channel is not None:
            if not self.music_player.connected_channel.is_paused() and self.music_player.connected_channel.is_playing():
                self.music_player.pause()

    async def resume(self):
        if self.music_player.connected_channel is not None:
            self.music_player.resume_playing()

    async def skip(self):
        if self.music_player.connected_channel is not None:
            if self.music_player.connected_channel.is_playing():
                self.music_player.stop_playing()

    async def seek(self, time:str):
        if not re.match(r'[:0-9]{1,8}', time):
            raise InvalidArgumentFormat(f'Time argument "{str}" for seek command invalid.')

        time = time.split(sep=':')
        while len(time) > 3:
            time.pop(0)
        while len(time) < 3:
            time.insert(0, '0')
        for i in range(0, len(time)):
            time[i] = int(time[i])
            if time[i] > 59:
                time[i] = 59
            if i == 0 and time[i] > 23:
                time[i] = 23

        timeD = datetime.time(time[0], time[1], time[2])
        print(time)
        song = (self.music_player.queue[0][0], self.music_player.queue[0][1], self.music_player.queue[0][2])
        if self.music_player.connected_channel is not None:
            self.music_player.register_song(song, time=timeD)
            self.music_player.stop_playing()