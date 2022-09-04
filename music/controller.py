import os
from io import TextIOWrapper
import json
import datetime
import re

import globals
from music.player import Player, Song
from exceptions import InvalidArgumentFormat

from discord.guild import Guild
from discord.member import Member
from discord.user import User
from discord.ext.commands import Context

from database.db_controller import database

import asyncio


class Controller:
    # list containing lambdas referring to functions, used to ensure programs execute one after the other

    def __init__(self, guild:Guild=None, bot=None):
        if guild is None:
            raise TypeError('Guild cannot be none!')
            return None

        self.cmd_queue = []
        self.config = {}
        
        self.guild = guild
        guild_name = guild.name
        self.config_path = globals.SERVER_FOLDER + '/' + guild.name + '/' + 'music.json'

        self.music_player = Player(self.after_song) #instantiates the music client

        self.timer_task = None #contains reference to task with timer
        self.timer = 0

        #default config template
        configData = {
            "owner": None,
            "users": {}, #inside values must be "username":"blacklist | whitelist | admin" , tuple user + value
            "forceTextChannel" : None, #force bot to only answer and reply in said channel
            "forceVoiceChannel" : None, #force bot to only play in certain void channel
            "whitelist" : False, #boolean to only allow whitelisted users call commands
        }

        if not os.path.exists(self.config_path):
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            f = open(self.config_path, 'w')
            f.write(json.dumps(configData,indent=3))
            f.close()
        
        #loads current config
        f = open(self.config_path)
        fstr:str = ''
        for line in f:
            fstr = fstr + line
        f.close()
        self.config = json.loads(fstr)

        self.setting_controller = SettingController(self)

        self.bot = bot

    def after_song(self):
        """
        Gets called after a song ends playing
        """
        if len(self.music_player.queue) > 0:
            self.timer_task.cancel()
            self.timer = 0
            self.music_player.start_playing()
            self.timer_task = self.bot.loop.create_task(self.timer_task_coro())
        else:
            self.bot.loop.create_task(self.music_player.connected_channel.disconnect())
            self.timer_task.cancel()
            self.timer = 0
            self.music_player.connected_channel = None

    async def play_url(self, url, caller:Member, ctx):
        if caller.voice is not None:
            song = self.music_player.extract_info(url)
            with database:
                database.register_song(song, caller.id, ctx.guild.id)
            self.music_player.register_song(song)

            # Avoid connecting if already connected
            if self.music_player.connected_channel is None:
                try:
                    await self.music_player.connect_channel(caller.voice.channel)
                except Exception as e:
                    pass #do something

            if not self.music_player.connected_channel.is_playing():
                self.timer_task = self.bot.loop.create_task(self.timer_task_coro())
                self.music_player.start_playing()

    async def play_query(self, query, caller: Member, ctx):
        if caller.voice is not None:
            try:
                id = self.music_player.query_extract(query)
            except Exception:
                await ctx.send("```Put a non playlist url for fucks sake```")
                return None
            song = self.music_player.extract_info(id)
            with database:
                database.register_song(song, caller.id, ctx.guild.id)
            self.music_player.register_song(song)

            if self.music_player.connected_channel == None:
                try:
                    await self.music_player.connect_channel(caller.voice.channel)
                except Exception as e:
                    pass #do something

            if not self.music_player.connected_channel.is_playing():
                self.timer_task = self.bot.loop.create_task(self.timer_task_coro())
                self.music_player.start_playing()

    async def pause(self):
        if self.music_player.connected_channel is not None:
            if not self.music_player.connected_channel.is_paused() and self.music_player.connected_channel.is_playing():
                self.timer_task.cancel()
                self.music_player.pause()

    async def resume(self):
        if self.music_player.connected_channel is not None:
            self.timer_task = self.bot.loop.create_task(self.timer_task_coro())
            self.music_player.resume_playing()

    async def skip(self):
        if self.music_player.connected_channel is not None:
            if self.music_player.connected_channel.is_playing():
                self.music_player.stop_playing()

    async def skip_all(self):
        if self.music_player.connect_channel is not None:
            self.music_player.queue = ['LMAO']
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
        timeSec = timeD.hour * 3600 + timeD.minute * 60 + timeD.second
#        song = (self.music_player.queue[0][0], self.music_player.queue[0][1], self.music_player.queue[0][2])
        song = Song()
        song.name = self.music_player.queue[0].name
        song.duration = self.music_player.queue[0].duration
        song.link = self.music_player.queue[0].link

        if timeSec > self.music_player.queue[0].duration:
            timeD = datetime.time(0,0,0)
            timeSec = 0
        
        if self.music_player.connected_channel is not None:
            self.music_player.register_song(song, time=timeD)
            self.music_player.stop_playing()
            await asyncio.sleep(1)
            self.timer = timeSec

    async def query_queue(self, ctx:Context):
        i = 0
        accumulated_est = 0
        msg:str = ''
        for s in self.music_player.queue:
            title, duration = s.name, s.duration
            hh, mm, ss = s_to_h(duration)
            hh, mm, ss = f'{hh:02d}',f'{mm:02d}',f'{ss:02d}'
            dur_str = f'{hh}:{mm}:{ss}' if int(hh) > 0 else f'{mm}:{ss}'

            msg += f'{i + 1}: {title}'
            if i == 0:
                hh, mm, ss = s_to_h(self.timer)
                hh, mm, ss = f'{hh:02d}',f'{mm:02d}',f'{ss:02d}'
                dur_str_current = f'{hh}:{mm}:{ss}' if int(hh) > 0 else f'{mm}:{ss}'
                msg = f'{msg} - {dur_str_current}/{dur_str} (CURRENT)\n'

                accumulated_est += duration - self.timer
            else:
                hh, mm, ss = s_to_h(accumulated_est)
                hh, mm, ss = f'{hh:02d}',f'{mm:02d}',f'{ss:02d}'
                dur_str_accumulated = f'{hh}:{mm}:{ss}' if int(hh) > 0 else f'{mm}:{ss}'
                msg = f'{msg} - {dur_str} -> (est. {dur_str_accumulated})\n'
                accumulated_est += duration
            i += 1
        
        if len(self.music_player.queue) > 0:
            await ctx.send(f'```{msg}```')

    async def timer_task_coro(self):
        try:
            while True:
                await asyncio.sleep(1)
                self.timer += 1
        except:
            pass

class SettingController():
    def __init__(self, parent):
        self.controller:Controller = parent

    def save_config(func):
        """
        Decorator to save to config file after executing a config changing function
        """
        def wrapper(*args, **kwargs):
            ret = func(*args, **kwargs)
            f = open(args[0].controller.config_path, 'w')
            f.write(json.dumps(args[0].controller.config,indent=3))
            f.close()
            return ret
        return wrapper

    @save_config
    def music_add_user(self, user:User, rank:str):
        if self.controller.config["users"].get(str(user.id)) != 'admin':
            self.controller.config["users"][str(user.id)] = rank

    @save_config
    def music_remove_user(self, user:User):
        if str(user.id) in self.controller.config["users"].keys():
            if self.controller.config["users"].get(str(user.id)) != 'admin':
                self.controller.config["users"].pop(str(user.id))

    @save_config
    def music_remove_admin(self, user:User):
        if str(user.id) in self.controller.config["users"].keys():
            self.controller.config["users"].pop(str(user.id))
        
    @save_config
    def toggle_whitelist_mode(self):
        self.controller.config["whitelist"] = not self.controller.config["whitelist"]

    @save_config
    def register_owner(self, user:User):
        self.controller.config["owner"] = str(user.id)

    def check_user_privilege(self, user:User, elevated=False) -> bool:
        """
        Check if a certain user is allowed to execute music commands.
        Takes in a discord.User object.

        Pass elevated=True for when checking admin commands
        """
        privilege = self.controller.config['users'].get(str(user.id))
        is_whitelist = self.controller.config['whitelist']

        if not elevated:
            if is_whitelist:
                if privilege in ('whitelist','admin') or self.controller.config["owner"] == str(user.id):
                    return True
            else:
                if privilege != 'blacklist':
                    return True
        else:
            if privilege == 'admin' or self.controller.config["owner"] == str(user.id):
                return True

        return False

    async def query_settings(self, ctx:Context):
        msg = f'```{json.dumps(self.controller.config, indent=3)}```'
        await ctx.send(msg)

def s_to_h(duration):
    return int(duration / 3600), int(duration / 60) % 60, duration % 60