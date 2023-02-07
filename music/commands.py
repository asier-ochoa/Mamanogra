from functools import wraps
from typing import Callable

import discord
from discord import Message, TextChannel, Embed, Activity, ActivityType, Member, Intents
from discord.ext import commands, tasks
from discord.ext.commands import Context
from music.controller import Controller
from database.db_controller import database
from config import config

from datetime import datetime
import asyncio


def db_command_log(func: Callable):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        ctx = None
        for a in args:
            if isinstance(a, Context):
                ctx = a
        with database:
            database.log_command(ctx.message.content, ctx.author.id, ctx.guild.id)
        return await func(*args, **kwargs)
    return wrapper


# ====Commands here==== 
class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @db_command_log
    async def info(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        await ctx.send(content=f"```Mamanogra v0.13 - I've got your data buddy :)\nMade by Smug Twingo\nUptime: {datetime.now() - started_time}```")

    @commands.command(name='help', aliases=['h'])
    @db_command_log
    async def help_c(self, ctx:Context):
        await ctx.send(help_str)

    @commands.command(aliases=['p'])
    @db_command_log
    async def play(self, ctx:Context, *, query):
        ctrl = find_controller(ctx.guild)
        if ctrl.setting_controller.check_user_privilege(ctx.author):
            embeds = ctx.message.embeds
            if len(embeds) != 0:
                link:Embed = embeds[0]
                ctrl.cmd_queue.append((ctrl.play_url, (link.url, ctx.author, ctx)))
            else:
                ctrl.cmd_queue.append((ctrl.play_query, (query, ctx.author, ctx)))

    @commands.command()
    @db_command_log
    async def pause(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        if ctrl.setting_controller.check_user_privilege(ctx.author):
            ctrl.cmd_queue.append((ctrl.pause, ()))

    @commands.command()
    @db_command_log
    async def resume(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        if ctrl.setting_controller.check_user_privilege(ctx.author):
            ctrl.cmd_queue.append((ctrl.resume, ()))

    @commands.command(aliases=['s'])
    @db_command_log
    async def skip(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        if ctrl.setting_controller.check_user_privilege(ctx.author):
            ctrl.cmd_queue.append((ctrl.skip, ()))

    @commands.command()
    @db_command_log
    async def clear(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        if ctrl.setting_controller.check_user_privilege(ctx.author):
            ctrl.cmd_queue.append((ctrl.skip_all, ()))

    @commands.command()
    @db_command_log
    async def seek(self, ctx:Context, seek:str):
        ctrl = find_controller(ctx.guild)
        if ctrl.setting_controller.check_user_privilege(ctx.author):
            ctrl.cmd_queue.append((ctrl.seek, (seek)))

    @commands.command(aliases=['q'])
    @db_command_log
    async def queue(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        ctrl.cmd_queue.append((ctrl.query_queue,(ctx)))


class SettingsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.group(invoke_without_command=True)
    async def config(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        await ctrl.setting_controller.query_settings(ctx)

    @config.command()
    async def whitelist(self, ctx:Context, *, user):
        ctrl = find_controller(ctx.guild)
        if ctrl.setting_controller.check_user_privilege(ctx.author, elevated=True):
            member = await ctx.guild.query_members(query = user)

            if len(member) > 0:
                member = member[0]
                ctrl.setting_controller.music_add_user(member, 'whitelist')

    @config.command()
    async def blacklist(self, ctx:Context, *, user):
        ctrl = find_controller(ctx.guild)
        if ctrl.setting_controller.check_user_privilege(ctx.author, elevated=True):
            member = await ctx.guild.query_members(query = user)

            if len(member) > 0:
                member = member[0]
                ctrl.setting_controller.music_add_user(member, 'blacklist')

    @config.command()
    async def delist(self, ctx:Context, *, user):
        ctrl = find_controller(ctx.guild)
        if ctrl.setting_controller.check_user_privilege(ctx.author, elevated=True):
            member = await ctx.guild.query_members(query = user)

            if len(member) > 0:
                member = member[0]
                ctrl.setting_controller.music_remove_user(member)

    @config.command()
    async def admin(self, ctx:Context, *, user):
        ctrl = find_controller(ctx.guild)
        if str(ctx.author.id) == ctrl.config["owner"]:
            member = await ctx.guild.query_members(query = user)

            if len(member) > 0:
                member = member[0]
                ctrl.setting_controller.music_add_user(member, 'admin')

    @config.command()
    async def deadmin(self, ctx:Context, *, user):
        ctrl = find_controller(ctx.guild)
        if str(ctx.author.id) == ctrl.config["owner"]:
            member = await ctx.guild.query_members(query = user)

            if len(member) > 0:
                member = member[0]
                ctrl.setting_controller.music_remove_admin(member)

    @config.command()
    async def toggle(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        if ctrl.setting_controller.check_user_privilege(ctx.author, elevated=True):
            ctrl.setting_controller.toggle_whitelist_mode()


class QueryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.command()
    @db_command_log
    async def top(self, ctx: Context, *args):
        with database:
            if len(args) > 0 and args[0] == 'global':
                scope = 'Global'
                author = ctx.author.display_name
                top_songs = [x for x in database.get_top_songs_global(ctx.author.id)]
            elif len(args) > 0 and args[0] == 'server':
                scope = 'Server'
                author = ctx.guild.name
                top_songs = [x for x in database.get_top_songs_server(ctx.guild.id)]
            else:
                scope = 'Local'
                author = ctx.author.display_name
                top_songs = [x for x in database.get_top_songs_local(ctx.author.id, ctx.guild.id)]
        message = f'\n**{scope} top for {author}**\n```\n'
        i = 0
        for s in top_songs:
            message += f'{i+1}. {s[0]}, {s[1]}, {s[2]}\n'
            i += 1
        message += '```'
        await ctx.channel.send(content=message)
# ====main function below this line====


# -----Pre Setup------
async def disc_setup():
    intent = Intents(members=True, guilds=True, voice_states=True, messages=True)
    intent = Intents.default()
    intent.members = True
    intent.guilds = True
    intent.voice_states = True
    intent.message_content = True
    intent.messages = True

    bot = commands.Bot(command_prefix='+', strip_after_prefix=True, intents=intent)
    bot.remove_command('help')
    await bot.add_cog(MusicCog(bot))
    await bot.add_cog(SettingsCog(bot))
    await bot.add_cog(QueryCog(bot))

    @bot.event
    async def on_ready():
        await setup_post(bot)
        print(bot.user.name + ' has succesfully logged in!')

    async with bot:
        await bot.start(config.discord.token)


# --------------------

started_time = datetime.now()
music_ctrl_list: list[tuple[Controller, discord.Guild]] = [] #list containing a touple of every instance of the bot in a server and every guild
# ex: [(<controller>,<guild>),...,('controller1','Punishment Zone')]
help_str = """```
===List of Music commands===
- play {url | query}      <-> Plays song or adds song to queue and connects bot to voice channel
- queue                   <-> Query the queue
- pause                   <-> Don't be retarded
- resume                  <-> Don't be retarded
- skip                    <-> Skips current song (Don't be retarded)
- clear                   <-> Removes all songs from queue and skips current song
- seek {%H:%M:%S}         <-> Seeks to the given timestamp in a song. If timestamp is invalid restarts the song
- top ->                  <-> Displays most played songs in this server
      -> global           <-> Displays most played songs in all servers
      -> server           <-> Displays most played songs by everyone in this server
```"""


def find_controller(guild) -> Controller:
    """
    Iterates through list of touples and returns controller to corresponding guild
    """
    global music_ctrl_list
    for t in music_ctrl_list:
        if t[1] == guild:
            return t[0]


async def setup_post(bot):
    with database:
        for i, guild in enumerate(bot.guilds):
            ctrl = Controller(guild=guild, bot=bot)
            music_ctrl_list.append((ctrl, guild))
            if guild.owner is not None:
                ctrl.setting_controller.register_owner(guild.owner)
            bot.loop.create_task(cmd_loop(ctrl))

            print(f"[Database] Registering server {guild.name}, {i + 1}/{len(bot.guilds)}")
            database.register_users([(x.id, x.name) for x in guild.members])
            database.register_server(guild.id, guild.name, guild.owner.id)
            database.register_memberships(guild.id, [m.id for m in guild.members])
        
    # Display number of connected servers
    x = len(bot.guilds)
    await bot.change_presence(activity=Activity(type=1, name=f'on {x} servers'))

lock = asyncio.Lock()


async def cmd_loop(ctrl:Controller):
    """
    Loop that executes a certain command queue.
    Pulls double duty and verifies permissions
    """
    while True:
        global lock
        await asyncio.sleep(0.2)
        async with lock:
            if len(ctrl.cmd_queue) > 0:
                params = ctrl.cmd_queue[0][1]
                if isinstance(params, tuple):
                    await ctrl.cmd_queue[0][0](*params)
                else:
                    await ctrl.cmd_queue[0][0](params)
                ctrl.cmd_queue.pop(0)