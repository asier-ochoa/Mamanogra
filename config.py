import json
import os.path
from typing import Union


class Configurator:
    class Discord:
        def __init__(self):
            self.token: Union[None, str] = ""

    class Server:
        def __init__(self):
            self.port: Union[None, int] = 5000

    def __init__(self):
        self.config_template = {
            "discord": {
                "token": ""
            },
            "server": {
                "port": 5000
            }
        }

        self.discord = self.Discord()
        self.server = self.Server()

        if not os.path.exists("config.json"):
            with open("config.json", "w") as f:
                json.dump(self.config_template, f, indent=4)
                print("Warning: Generated missing config.json, please fill it out and relaunch the program")
                exit(1)

        with open("config.json", "r") as f:
            conf_dict: dict = json.load(f)

        if not self.validate_config(conf_dict):
            print("Error: Invalid Config!")

    def validate_config(self, conf_input: dict, template: Union[dict, None] = None, self_translation=None):
        template = self.config_template if template is None else template
        self_translation = self if self_translation is None else self_translation
        for k, v in template.items():
            if k not in conf_input:
                return False
            if isinstance(conf_input[k], str) and conf_input[k] == "":
                return False
            if not isinstance(conf_input[k], type(v)):
                return False
            if isinstance(v, dict):
                if not self.validate_config(conf_input[k], v, self_translation.__getattribute__(k)):
                    return False
            else:
                self_translation.__setattr__(k, conf_input[k])

        return True


def _setattr_override(self, key, value):
    raise AttributeError("Can't set configuration values!")


config = Configurator()
Configurator.__setattr__ = _setattr_override