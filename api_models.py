from pydantic import BaseModel


class PlaySongModel(BaseModel):
    voice_channel_id: int
    guild_id: int
    song: str
