import json
import os.path
from json import JSONDecodeError

from pydantic import BaseModel, ValidationError


class DiscordModel(BaseModel):
    token: str
    info_message: str


class ServerModel(BaseModel):
    port: int


class Configuration(BaseModel):
    discord: DiscordModel
    server: ServerModel


# Start of configuration, shall only run the first time this module is imported
if not os.path.exists("config.json"):
    # Generate config template
    with open("config.json", "w") as f:
        json.dump(Configuration.construct(
            discord=DiscordModel(
                token="",
                info_message="",
            ),
            server=ServerModel(
                port=5000
            )
        ).dict(), f, indent=4)
        print("Warning: Generated missing config.json, please fill it out and relaunch the program")
        exit(1)

with open("config.json", "r") as f:
    try:
        conf_dict: dict = json.load(f)
    except JSONDecodeError:
        print("Error: Invalid JSON format in config, can't parse config.json! Deleting the file causes it to be regenerated.")
        exit(1)

try:
    config = Configuration(**conf_dict)
except ValidationError as exc:
    print(f"Error: Invalid Config! Details: {exc.json(indent=4)}")
    exit(1)
