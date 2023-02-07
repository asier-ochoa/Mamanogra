from music.commands import disc_setup
from flask import Flask
import api
import asyncio
import threading


def run_flask():
    app = Flask(__name__)
    app.register_blueprint(api.bp)
    app.run()


flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

asyncio.run(disc_setup())
