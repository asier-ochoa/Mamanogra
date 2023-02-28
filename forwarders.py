from discord import Message, Member, VoiceState
import global_state
from discord_server import Server


async def forward_message_to_server(message: Message):
    async with global_state.guild_server_map_lock:
        if global_state.guild_server_map.get(message.guild.id) is not None:
            server: Server = global_state.guild_server_map[message.guild.id]
        else:
            # possible place to handle direct messages
            return
    await server.message_entrypoint(message)


async def forward_voice_state_to_server(member: Member, before: VoiceState, after: VoiceState):
    async with global_state.guild_server_map_lock:
        # Only forward to server if the bot was updated
        if member == global_state.discord_client.user:
            if global_state.guild_server_map.get(member.guild.id) is not None:
                server: Server = global_state.guild_server_map[member.guild.id]
        else:
            return
    await server.voice_state_entrypoint(before, after)
