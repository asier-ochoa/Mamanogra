import time
from datetime import datetime, timedelta

from discord import Member, VoiceChannel
from flask import Response, request, g
from flask.blueprints import Blueprint
from pydantic import ValidationError

import global_state
import utils
from api_models import PlaySongModel
from config import config
import discord
from db_controller import database, WebKeyStatus
from song_generators import generate_youtube_song

bp = Blueprint('bp', __name__)


@bp.errorhandler(ValidationError)
def handle_validation_error(err: ValidationError):
    return err.errors(), 400


@bp.before_request
def auth_key():
    if 'keygen' not in request.path:
        key = request.cookies.get('key')
        if key is None:
            return "No key", 403
        with database:
            is_auth, key_status = database.auth_key(key)

        if not is_auth:
            return "key invalid", 403
        g.user = key_status


@bp.get('/keygen/<token>')
def validate_key(token: str):
    with database:
        status = database.get_web_key_with_token(token)

    if status is None:
        return "Couldn't find token", 404
    if status.validated:
        return "You already have a key, forwarding to dashboard"
    if status.request_token_expiration_date < datetime.now():
        return "URL is expired, please generate a new one using \"+w\"", 403

    with database:
        database.validate_key(status.id)
    resp = Response("Key generated and saved in your cookies, forwarding to dashboard")
    resp.set_cookie(key='key', value=status.key, expires=datetime.now() + timedelta(days=91))
    return resp


@bp.get('/api/guilds')
def get_guilds():
    user: WebKeyStatus = g.user
    with database:
        guild_ids = database.get_all_user_servers(user.id)

    guilds = [
        {
            "name": guild.name,
            "disc_id": guild.id,
            "thumbnail": guild.icon.url
        } for guild in
        global_state.discord_client.guilds
        if guild.id in guild_ids
    ]

    return guilds


@bp.get('/api/guilds/<guild_id>')
def get_guild_detail(guild_id: str):
    user: WebKeyStatus = g.user
    with database:
        guild_ids = database.get_all_user_servers(user.id)
    if int(guild_id) not in guild_ids:
        return "Current user is not a member", 403

    return {
        "voice_channels": [
            {
                "name": x.name,
                "id": x.id
            } for x in
            global_state.guild_server_map[int(guild_id)].disc_guild.voice_channels
        ],
        "text_channels": [
            {
                "name": x.name,
                "id": x.id
            } for x in
            global_state.guild_server_map[int(guild_id)].disc_guild.text_channels
        ]
    }


@bp.post('/api/playUrl')
def play_song():
    user: WebKeyStatus = g.user
    with database:
        disc_id = database.cur.execute(
            """
            SELECT discord_id FROM users
            where id = ?
            """, [user.id]
        ).fetchone()[0]

    body = PlaySongModel(**request.get_json())
    server = global_state.guild_server_map.get(body.guild_id)
    disc_usr: Member = discord.utils.get(server.disc_guild. members, id=int(disc_id))
    voice_channel: VoiceChannel = discord.utils.get(server.disc_guild.voice_channels, id=body.voice_channel_id)

    if None in (disc_usr, voice_channel, server):
        return "Incorrect guild or voice channel id", 400

    # Launch coroutine so that the api call is non-blocking
    async def play_coro_wrapper():
        await server.music_player.play(
            disc_usr,
            await generate_youtube_song(body.song),
            voice_channel
        )
    global_state.discord_client.loop.create_task(
        play_coro_wrapper()
    )

    return 'OK'


@bp.get('/api/queue/<guild_id>')
def get_queue(guild_id: str):
    user: WebKeyStatus = g.user
    with database:
        guild_ids = database.get_all_user_servers(user.id)
    if int(guild_id) not in guild_ids:
        return "Current user is not a member", 403

    srv = global_state.guild_server_map[int(guild_id)]
    return {
        "current_index": srv.music_player.current_index,
        "queue": [
            {
                "song_details": utils.get_function_default_args(x.source_func),
                "requester": {
                    "name": x.requester.name,
                    "id": x.requester.id
                },
                "time_played": x.time_played.isoformat(),
                "time_requested": x.time_requested.isoformat()
            } for x in srv.music_player.queue
        ]
    }
