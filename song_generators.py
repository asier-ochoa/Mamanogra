from copy import deepcopy
from datetime import timedelta
from typing import Optional, Callable

from discord import FFmpegPCMAudio
from yt_dlp import YoutubeDL

FFMPEG_YT_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}


# Use factory pattern to embed different types of playable audio as a function
async def generate_youtube_song(yt_id: str, e_seek: Optional[int] = None) -> Callable[[], FFmpegPCMAudio]:
    outer_yt_query = YoutubeDL(
        {'format': 'bestaudio/best', 'quiet': True, 'noplaylist': True}
    ).extract_info(yt_id, download=False)
    if yt_id.startswith("ytsearch:"):
        outer_yt_query = outer_yt_query['entries'][0]
    e_title, e_duration, e_thumbnail = outer_yt_query.get('title'), outer_yt_query.get('duration'), outer_yt_query.get('thumbnail')

    def youtube_song(i_yt_id=yt_id, seek=e_seek, title=e_title, duration=e_duration, thumbnail=e_thumbnail, db_youtube_id=outer_yt_query.get('id')):  # Default params for early binding
        ffmpeg_options = deepcopy(FFMPEG_YT_OPTIONS)
        # Add seeking if requested
        if seek is not None:
            seek_time = timedelta(seconds=seek)
            ffmpeg_options['before_options'] += ''.join([
                ' -ss ',
                f'{seek_time.seconds // 3600}:',
                f'{seek_time.seconds // 60 % 60}:',
                f'{seek_time.seconds % 60}'
            ])

        yt_query = YoutubeDL(
            {'format': 'bestaudio/best', 'quiet': True, 'noplaylist': True}
        ).extract_info(i_yt_id, download=False)
        if i_yt_id.startswith("ytsearch:"):
            yt_query = yt_query['entries'][0]
        audio_format: str = yt_query['format_id']
        audio_url = [
            x for x in yt_query['formats']
            if x['format_id'] == audio_format
        ][0]['url']

        # Make it so this function returns the audio_url instead of the FFmpegPCMAudio to allow for faster seeking
        # Ignore previous comment, use a cache with the url
        return FFmpegPCMAudio(source=audio_url, **ffmpeg_options)
    return youtube_song


async def generate_url_song(url: str) -> Callable[[], FFmpegPCMAudio]:
    e_title = url.split('/')[-1].split('.')[0]

    def url_song(i_url=url, seek=0, title=e_title):
        ffmpeg_options = {}
        if seek is not None:
            seek_time = timedelta(seconds=seek)
            ffmpeg_options['before_options'] = ''.join([
                ' -ss ',
                f'{seek_time.seconds // 3600}:',
                f'{seek_time.seconds // 60 % 60}:',
                f'{seek_time.seconds % 60}'
            ])
        return FFmpegPCMAudio(source=i_url, **ffmpeg_options)
    return url_song
