from datetime import datetime

from discord import Message, HTTPException, Forbidden
from yt_dlp import YoutubeDL

import utils
from config import config
import global_state

from discord_server import Server
from discord_server_commands import Command
from music_player import generate_youtube_song


async def info_command(msg: Message, srv: Server):
    try:
        await msg.channel.send(
            content="\n".join((
                "```",
                f"Mamanogra v0.13 - {config.discord.info_message}",
                "Made by Smug Twingo",
                f"Uptime: {str(datetime.now() - global_state.start_time).split('.')[0]}"
                "```"
            ))
        )
    # Make error messages more detailed
    except Forbidden as exc:
        print(f"Error: Insufficient permissions. Details: {exc.response}")
    except HTTPException as exc:
        print(f"Error: HTTPException while trying to write info message. Details: {exc.response}")


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
        msg.content.split(' ')[-1]
    )

    if yt_query['_type'] != 'playlist':
        print(f"Error: yt-dlp extraction using \"{msg.content.split(' ')[-1]}\" was not of playlist type")
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
    if 0 <= srv.music_player.current_index + n_times < len(srv.music_player.queue):
        async with srv.music_player.voice_client_lock:
            srv.music_player.current_index += n_times - 1
    else:
        if srv.music_player.current_index == len(srv.music_player.queue) - 1 and n_times == 1:
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


def get_defaults(prefix: str):
    commands = [
        (fr"\{prefix}(?:info$|i$)", info_command),
        (fr"\{prefix}(?:p |play )https:\/\/(?:(?:www\.youtube\.com\/.*?watch\?v=([\w\d\-\_]*).*)|(?:youtu\.be\/([\w\d\-\_]+)))", play_url_command),
        (fr"\{prefix}(?:p |play )([^|]+(?!\| \|)(?:\|(?:[^|]+))*)", play_query_command),
        (fr"\{prefix}(?:pl |playlist )https:\/\/www\.youtube\.com\/.*?list=([\w\d]*).*", play_playlist_command),
        (fr"\{prefix}(?:s |skip |s$|skip$)(?:(?!0)(?!-0)(-?\d+))?", skip_command),
        (fr"\{prefix}(?:q$|queue$)", queue_command),
        (fr"\{prefix}seek (\d?\d:\d\d:\d\d$|\d?\d:\d\d$)", seek_command)
    ]
    return [Command(*x) for x in commands]
