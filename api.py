import asyncio

from flask.blueprints import Blueprint
from flask import request
import music.player as player
from music.commands import controllers

bp = Blueprint('bp', __name__)


@bp.post("/play")
def do():
    body = request.get_json(force=True)
    ctrl = [x for x in controllers if x[1].name == "Punishment Zone"][0]
    caller = [x for x in ctrl[1].members if x.name == "Smug Twingo"][0]
    ctrl = ctrl[0]
    asyncio.ensure_future(ctrl.play_url(body['url'], caller), loop=ctrl.bot.loop)
    print("XD")
    return 'Done'
