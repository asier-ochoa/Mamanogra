from discord import Message, TextChannel, Embed
from discord.ext import commands, tasks
from discord.ext.commands import Context
from music.controller import Controller

from datetime import datetime
import asyncio

# ====Commands here==== 
class Music_cog(commands.Cog):
    @commands.command()
    async def info(self, ctx:Context):
        await ctx.send(content=f"```Mamanogra v0.1 - probably broken\nMade by Smug Twingo\nUptime: {datetime.now() - started_time}```")

    @commands.command()
    async def play(self, ctx:Context, *, query):
        ctrl = find_controller(ctx.guild)
        embeds = ctx.message.embeds
        if len(embeds) != 0:
            link:Embed = embeds[0]
            ctrl.cmd_queue.append((ctrl.play_url, (link.url, ctx.author)))
        else:
            ctrl.cmd_queue.append((ctrl.play_query, (query, ctx.author)))

    @commands.command()
    async def pause(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        ctrl.cmd_queue.append((ctrl.pause, ()))

    @commands.command()
    async def resume(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        ctrl.cmd_queue.append((ctrl.resume, ()))

    @commands.group()
    async def skip(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        ctrl.cmd_queue.append((ctrl.skip, ()))

    @skip.command()
    async def all(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        ctrl.cmd_queue.append((ctrl.skip_all, ()))

    @commands.command()
    async def seek(self, ctx:Context, seek:str):
        ctrl = find_controller(ctx.guild)
        ctrl.cmd_queue.append((ctrl.seek, (seek)))

# ====main function below this line====

# -----Pre Setup------
bot = commands.Bot(command_prefix='+')
bot.add_cog(cog=Music_cog())
# --------------------

started_time = datetime.now()
music_ctrl_list = [] #list containing a touple of every instance of the bot in a server and every guild
# ex: [(<controller>,<guild>),...,('controller1','Punishment Zone')]
help = """```
===List of Music commands===
++ {url | query} <-> Plays song or adds song to queue
+? <-> Query the queue
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
    async for guild in bot.fetch_guilds():
        ctrl = Controller(guild=guild, bot=bot)
        music_ctrl_list.append((ctrl, guild))
        bot.loop.create_task(cmd_loop(ctrl))

lock = asyncio.Lock()

async def cmd_loop(ctrl:Controller):
    """
    Loop that executes a certain command queue.
    Pulls double duty and verifies permissions
    """
    while True:
        global lock
        await asyncio.sleep(1)
        async with lock:
            if len(ctrl.cmd_queue) > 0:
                params = ctrl.cmd_queue[0][1]
                if isinstance(params, tuple):
                    await ctrl.cmd_queue[0][0](*params)
                else:
                    await ctrl.cmd_queue[0][0](params)
                ctrl.cmd_queue.pop(0)