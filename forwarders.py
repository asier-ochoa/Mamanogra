from discord import Message
import global_state
from discord_server import Server


async def forward_message_to_server(message: Message):
    async with global_state.guild_server_map_lock:
        if global_state.guild_server_map.get(message.guild.id) is not None:
            server: Server = global_state.guild_server_map[message.guild.id]
            await server.message_entrypoint(message)
        else:
            # possible place to handle direct messages
            return
