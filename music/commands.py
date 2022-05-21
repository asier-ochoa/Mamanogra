from discord import Message, TextChannel, Embed, Activity, ActivityType, Member, Intents
from discord.ext import commands, tasks
from discord.ext.commands import Context
from music.controller import Controller

from datetime import datetime
import asyncio

# ====Commands here==== 
class Music_cog(commands.Cog):
    @commands.command()
    async def info(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        await ctx.send(content=f"```Mamanogra v0.11 - Now with permissions - still broken\nMade by Smug Twingo\nUptime: {datetime.now() - started_time}```")

    @commands.command(name='help', aliases=['h'])
    async def help_c(self, ctx:Context):
        await ctx.send(help_str)

    @commands.command(aliases=['p'])
    async def play(self, ctx:Context, *, query):
        ctrl = find_controller(ctx.guild)
        if ctrl.setting_controller.check_user_privilege(ctx.author):
            embeds = ctx.message.embeds
            if len(embeds) != 0:
                link:Embed = embeds[0]
                ctrl.cmd_queue.append((ctrl.play_url, (link.url, ctx.author)))
            else:
                ctrl.cmd_queue.append((ctrl.play_query, (query, ctx.author, ctx)))

    @commands.command()
    async def pause(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        if ctrl.setting_controller.check_user_privilege(ctx.author):
            ctrl.cmd_queue.append((ctrl.pause, ()))

    @commands.command()
    async def resume(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        if ctrl.setting_controller.check_user_privilege(ctx.author):
            ctrl.cmd_queue.append((ctrl.resume, ()))

    @commands.command(aliases=['s'])
    async def skip(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        if ctrl.setting_controller.check_user_privilege(ctx.author):
            ctrl.cmd_queue.append((ctrl.skip, ()))

    @commands.command()
    async def clear(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        if ctrl.setting_controller.check_user_privilege(ctx.author):
            ctrl.cmd_queue.append((ctrl.skip_all, ()))

    @commands.command()
    async def seek(self, ctx:Context, seek:str):
        ctrl = find_controller(ctx.guild)
        if ctrl.setting_controller.check_user_privilege(ctx.author):
            ctrl.cmd_queue.append((ctrl.seek, (seek)))

    @commands.command(aliases=['q'])
    async def queue(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        ctrl.cmd_queue.append((ctrl.query_queue,(ctx)))

class SettingsCog(commands.Cog):
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

# ====main function below this line====

# -----Pre Setup------
intent = Intents(members=True, guilds=True, voice_states=True, messages=True)
bot = commands.Bot(command_prefix='+',strip_after_prefix=True, intents=intent)
bot.remove_command('help')
bot.add_cog(cog=Music_cog())
bot.add_cog(cog=SettingsCog())
# --------------------

started_time = datetime.now()
music_ctrl_list = [] #list containing a touple of every instance of the bot in a server and every guild
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
```"""

def find_controller(guild) -> Controller:
    """
    Iterates through list of touples and returns controller to corresponding guild
    """
    global music_ctrl_list
    for t in music_ctrl_list:
        if t[1] == guild:
            return t[0]

@bot.event
async def on_ready():
    await setup_post()
    print(bot.user.name + ' has succesfully logged in!')

async def setup_post():
    global bot
    for guild in bot.guilds:
        ctrl = Controller(guild=guild, bot=bot)
        music_ctrl_list.append((ctrl, guild))
        if guild.owner is not None:
            ctrl.setting_controller.register_owner(guild.owner)
        bot.loop.create_task(cmd_loop(ctrl))
        
    #Display number of connected servers
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
        await asyncio.sleep(0.5)
        async with lock:
            if len(ctrl.cmd_queue) > 0:
                params = ctrl.cmd_queue[0][1]
                if isinstance(params, tuple):
                    await ctrl.cmd_queue[0][0](*params)
                else:
                    await ctrl.cmd_queue[0][0](params)
                ctrl.cmd_queue.pop(0)