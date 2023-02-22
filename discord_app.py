from datetime import datetime
from typing import Union

from config import config
from discord import Client, Intents, Message, Guild, Member, Reaction, User

import global_state
from discord_server import Server
from forwarders import forward_message_to_server


async def event_setup(client: Client):
    # Commands entrypoint

    @client.event
    async def on_message(message: Message):
        await forward_message_to_server(message)  # Function to move execution over to related server

    @client.event
    async def on_member_join(member: Member):
        await forward_member_to_server()

    @client.event
    async def on_reaction_add(reaction: Reaction, user: Union[Member, User]):
        pass forward_reaction_to_server()

    @client.event
    async def on_guild_join(guild: Guild):
        await register_server(guild)

    @client.event
    async def on_guild_remove(guild: Guild):
        await remove_server(guild)


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

    await event_setup(main_client)

    await main_client.start(token=config.discord.token, reconnect=True)

#-------------- Internal guild map update --------------
async def register_server(guild: Guild):
    with global_state.guild_server_map_lock:
        global_state.guild_server_map[guild.id] = Server(guild)
        global_state.server_membership_count += 1

async def remove_server(guild: Guild):
    with global_state.guild_server_map_lock:
        global_state.guild_server_map.pop(guild.id)
        global_state.server_membership_count -= 1
