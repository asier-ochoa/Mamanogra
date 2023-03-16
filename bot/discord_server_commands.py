import re
from typing import Any, Callable, Awaitable

from discord import Message


class Command:
    """
    POD-like class to hold data about a command
    """
    def __init__(self, regex: str, delegate: Callable[[Message, Any, ...], Awaitable[Any]]):
        self.regex: re.Pattern = re.compile(regex)
        self.delegate = delegate
