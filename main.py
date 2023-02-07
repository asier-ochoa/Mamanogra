from music.commands import disc_setup
from flask import Flask
import asyncio
import threading


def run_flask():
    app = Flask(__name__)
    app.run()


flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

asyncio.run(disc_setup())
