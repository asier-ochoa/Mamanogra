import asyncio
from datetime import datetime

import bot.discord_default_global_commands as discord_default_global_commands
import bot.discord_default_music_commands as discord_default_music_commands
from config import config
from discord import Client, Intents, Message, Guild, Member, VoiceState, RawMemberRemoveEvent

import global_state
from database.db_controller import database
from bot.discord_server import Server
from bot.forwarders import forward_message_to_server, forward_voice_state_to_server


async def event_setup(client: Client):
    # Commands entrypoint

    @client.event
    async def on_message(message: Message):
        await forward_message_to_server(message)  # Function to move execution over to related server

    @client.event
    async def on_member_join(member: Member):
        with database:
            database.register_users([(member.id, member.name)])
            database.register_memberships(member.guild.id, [member.id])
        print(f"Info: {member.name}#{member.discriminator} joined guild \'{member.guild.name}\'")

    @client.event
    async def on_raw_member_remove(payload: RawMemberRemoveEvent):
        with database:
            database.remove_membership(payload.guild_id, payload.user.id)
        print(f"Info: {payload.user.name}#{payload.user.discriminator} left guild \'{global_state.guild_server_map[payload.guild_id].disc_guild.name}\'")

    # @client.event
    # async def on_reaction_add(reaction: Reaction, user: Union[Member, User]):
    #     pass forward_reaction_to_server()

    @client.event
    async def on_voice_state_update(member: Member, before: VoiceState, after: VoiceState):
        await forward_voice_state_to_server(member, before, after)

    @client.event
    async def on_guild_join(guild: Guild):
        await register_server(guild)

    @client.event
    async def on_guild_remove(guild: Guild):
        await remove_server(guild)


async def register_if_alive():
    """
    Coroutine task that periodically runs and registers to database the bots status
    """
    while True:
        await asyncio.sleep(config.discord.is_alive_interval.seconds)


async def setup():
    # Setup Intents
    intent = Intents.default()
    intent.members = True
    intent.guilds = True
    intent.voice_states = True
    intent.message_content = True
    intent.messages = True
    intent.reactions = True

    # Declare reference to client
    main_client = Client(intents=intent)
    global_state.discord_client = main_client

    await event_setup(main_client)

    # Set any recurring tasks
    main_client.loop.create_task(register_if_alive())

    # Startup event
    @main_client.event
    async def on_ready():
        global_state.start_time = datetime.now()

        for g in main_client.guilds:
            await register_server(g)

        for s in global_state.guild_server_map.values():
            s.register_commands(discord_default_global_commands.get_global_defaults(prefix='+'))
            s.register_commands(discord_default_music_commands.get_music_defaults(prefix='+'))

        print("Info: Discord bot initialized")

    await main_client.start(token=config.discord.token, reconnect=True)


# -------------- Internal guild map update --------------
async def register_server(guild: Guild):
    async with global_state.guild_server_map_lock:
        global_state.guild_server_map[guild.id] = Server(guild)
        global_state.server_membership_count += 1
    with database:
        database.register_users([(x.id, x.name) for x in guild.members])
        database.register_server(guild.id, guild.name, guild.owner.id)
        database.register_memberships(guild.id, [m.id for m in guild.members])
    print(f"Info: Bot joined guild \"{guild.name}\"")


async def remove_server(guild: Guild):
    async with global_state.guild_server_map_lock:
        global_state.guild_server_map.pop(guild.id)
        global_state.server_membership_count -= 1
    print(f"Info: Bot was removed from guild \"{guild.name}\"")
