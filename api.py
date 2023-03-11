from datetime import datetime

from flask import Response
from flask.blueprints import Blueprint

from db_controller import database

bp = Blueprint('bp', __name__)


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
    resp.set_cookie(key='key', value=status.key)
    return resp
