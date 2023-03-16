from bot import discord_app
from config import config

from flask import Flask
import api
import asyncio
import threading


def run_flask():
    app = Flask(__name__)
    app.register_blueprint(api.bp)
    app.run(port=config.server.port)


flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

asyncio.run(discord_app.setup())
