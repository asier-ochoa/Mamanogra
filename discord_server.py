from discord import Guild


class Server:
    """
    Used to internally represent a discord guild
    Contains commands, music queue
    """
    def __init__(self, guild: Guild):
        
