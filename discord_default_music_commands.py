import random
from typing import Optional, Literal

from discord import Message
from yt_dlp import YoutubeDL

import utils
from db_controller import database

from discord_server import Server
from discord_server_commands import Command
from song_generators import generate_youtube_song, generate_url_song


async def play_url_command(msg: Message, srv: Server, yt_id: str = None):
    print(f"Info: {msg.author.name}#{msg.author.discriminator} queued youtube ID \"{yt_id}\"")
    await srv.music_player.play(msg.author, await generate_youtube_song(yt_id))


async def play_query_command(msg: Message, srv: Server, query: str = None):
    queries = query.split('|')
    if len(queries) == 1:
        print(f"Info: {msg.author.name}#{msg.author.discriminator} queuing single query \"{query}\"")
        await srv.music_player.play(msg.author, await generate_youtube_song(f"ytsearch:{queries[0]}"))
    else:
        print(f"Info: {msg.author.name}#{msg.author.discriminator} queuing multi query \"{query}\"")
        for q in queries:
            await srv.music_player.play(msg.author, await generate_youtube_song(f"ytsearch:{q}"))


async def play_playlist_command(msg: Message, srv: Server, yt_id: str = None):
    yt_query = YoutubeDL({
        'format': 'bestaudio/best',
        'quiet': True,
        'extract_flat': True,
        'playlist_items': '1:10'
    }).extract_info(
        msg.content.split(' ')[-1],
        download=False
    )

    if yt_query['_type'] != 'playlist':
        print(f"Error: yt-dlp extraction using \"{msg.content.split(' ')[-1]}\" was not of playlist type")
        await msg.channel.send("```\nCannot access this playlist!\n```")
        return

    print(f"Info: Queuing playlist \"{yt_query['title']}\" requested by {msg.author.name}#{msg.author.discriminator} using \"{msg.content.split(' ')[-1]}\"")
    for e in yt_query['entries']:
        await srv.music_player.play(
            msg.author,
            await generate_youtube_song(e['id'])
        )


async def skip_command(msg: Message, srv: Server, n_times_str: str = '1'):
    n_times = int(n_times_str)
    async with srv.music_player.voice_client_lock:
        if srv.music_player.voice_client is None:
            return
    print(f"Info: {msg.author.name}#{msg.author.discriminator} skipped {n_times} song(s) in {srv.disc_guild.name}")
    if 0 <= srv.music_player.current_index + n_times < len(srv.music_player.queue) and srv.music_player.voice_client.is_playing():
        async with srv.music_player.voice_client_lock:
            srv.music_player.current_index += n_times - 1
    else:
        if srv.music_player.current_index == len(srv.music_player.queue) - 1 and n_times == 1 and srv.music_player.voice_client.is_playing():
            pass  # If trying to skip last song, allow to go out of bounds
        else:
            return

    srv.music_player.voice_client.stop()


async def queue_command(msg: Message, srv: Server):
    await msg.channel.send(
        "".join([
            "```\n",
            "----Queue----\n\n",
            "\n".join(srv.music_player.print_queue()),
            "\n```"
        ])
    )


async def seek_command(msg: Message, srv: Server, timestamp: str):
    split_stamp = [int(x) for x in timestamp.split(':')]
    if not all(x < 60 for x in split_stamp):
        return
    if len(split_stamp) == 2:
        m, s = split_stamp
        sec_stamp = m * 60 + s
    else:
        h, m, s = split_stamp
        sec_stamp = h * 3600 + m * 60 + s

    # Modify current function's default args to include seeking
    cur_song_func = srv.music_player.queue[srv.music_player.current_index].source_func
    song_args = utils.get_function_default_args(cur_song_func)
    if 'seek' not in song_args:
        return
    song_args['seek'] = sec_stamp
    async with srv.music_player.voice_client_lock:
        cur_song_func.__defaults__ = tuple(song_args.values())
        srv.music_player.seek_flag = True
        srv.music_player.current_index -= 1

    print(f"Info: {msg.author.name}#{msg.author.discriminator} seeked to {timestamp}")
    srv.music_player.voice_client.stop()


async def shuffle_command(msg: Message, srv: Server):
    cur_idx = srv.music_player.current_index
    if cur_idx < len(srv.music_player.queue):
        async with srv.music_player.voice_client_lock:
            queue_slice = srv.music_player.queue[cur_idx + 1:]
            random.shuffle(queue_slice)
            srv.music_player.queue[cur_idx + 1:] = queue_slice
        print(f"Info: {msg.author.name}#{msg.author.discriminator} shuffled the queue in {srv.disc_guild.name}")


async def play_file_command(msg: Message, srv: Server, url: Optional[str] = None):
    i_url = url
    if len(msg.attachments) > 0:
        i_url = msg.attachments[0].url
    if i_url is None:
        return

    print(f"Info: {msg.author.name}#{msg.author.discriminator} queued audio url \"{url}\" in {srv.disc_guild.name}")
    await srv.music_player.play(msg.author, await generate_url_song(i_url))


async def top_command(msg: Message, srv: Server, q_type: Optional[Literal['global', 'server']] = None):
    with database:
        if q_type is None:
            scope = 'Local'
            author = msg.author.display_name
            top_songs = [x for x in database.get_top_songs_local(msg.author.id, msg.guild.id)]
        elif q_type == 'global':
            scope = 'Global'
            author = msg.author.display_name
            top_songs = [x for x in database.get_top_songs_global(msg.author.id)]
        elif q_type == 'server':
            scope = 'Server'
            author = msg.guild.name
            top_songs = [x for x in database.get_top_songs_server(msg.guild.id)]

    message = f'\n**{scope} top for {author}**\n```\n'
    i = 0
    for s in top_songs:
        message += f'{i + 1}. {s[0]}, {s[1]}, {s[2]}\n'
        i += 1
    message += '```'
    await msg.channel.send(content=message)


def get_music_defaults(prefix: str):
    commands = [
        (fr"\{prefix}(?:pe |play embed |pe$|play embed$)(.+\.(?:mp3$|ogg$|wav$|mp4$))?", play_file_command),
        (fr"\{prefix}(?:p |play )https:\/\/(?:(?:www\.youtube\.com\/.*?watch\?v=([\w\d\-\_]*).*)|(?:youtu\.be\/([\w\d\-\_]+)))", play_url_command),
        (fr"\{prefix}(?:p |play )([^|]+(?!\| \|)(?:\|(?:[^|]+))*)", play_query_command),
        (fr"\{prefix}(?:pl |playlist )https:\/\/www\.youtube\.com\/.*?list=([\w\d]*).*", play_playlist_command),
        (fr"\{prefix}(?:s |skip |s$|skip$)(?:(?!0)(?!-0)(-?\d+))?", skip_command),
        (fr"\{prefix}(?:sh$|shuffle$)", shuffle_command),
        (fr"\{prefix}(?:q$|queue$)", queue_command),
        (fr"\{prefix}seek (\d?\d:\d\d:\d\d$|\d?\d:\d\d$)", seek_command),
        (fr"\{prefix}top(?:$| (global$|server$))", top_command)
    ]
    return [Command(*x) for x in commands]
