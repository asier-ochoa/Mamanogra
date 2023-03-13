from datetime import datetime, timedelta

from flask import Response, request, g
from flask.blueprints import Blueprint

import global_state
from config import config
from db_controller import database, WebKeyStatus

bp = Blueprint('bp', __name__)


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

    print([x.id for x in global_state.discord_client.guilds])

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
