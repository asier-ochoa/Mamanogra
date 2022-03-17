from discord import Message, TextChannel
from discord.ext import commands, tasks
from discord.ext.commands import Context
from music.controller import Controller

from datetime import datetime
import asyncio

# list containing lambdas refering to functions
cmd_queue = []

# ====Commands here==== 
class Music_cog(commands.Cog):
    @commands.command()
    async def info(self, ctx:Context):
        await ctx.send(content=f"```Mamanogra v0.1 - probably broken\nMade by SmugTwingo\nUptime: {datetime.now() - started_time}```")

    @commands.command()
    async def play(self, ctx:Context, url:str):
        global cmd_queue
        ctrl = find_controller(ctx.guild)
        cmd_queue.append((ctrl.play_url, (url, ctx.author)))

    @commands.command()
    async def pause(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        await ctrl.pause()

    @commands.command()
    async def resume(self, ctx:Context):
        ctrl = find_controller(ctx.guild)
        await ctrl.resume()

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

def find_controller(guild):
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
    async for guild in bot.fetch_guilds():
        music_ctrl_list.append((Controller(guild=guild), guild))
    
    asyncio.get_running_loop().create_task(cmd_loop())

async def cmd_loop():
    global cmd_queue
    while True:
        await asyncio.sleep(1)
        if len(cmd_queue) > 0:
            params = cmd_queue[0][1]
            await cmd_queue[0][0](*params)
            cmd_queue.pop(0)