import os
from pathlib import Path
import requests
from io import BytesIO
from typing import List, Dict

from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_choice, create_option

from elasticsearch_conn import ElasticSearchConnector

env_path = Path('.') / '.env'

load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
slash = SlashCommand(bot, sync_commands=True)

es_client = ElasticSearchConnector(
    elastic_domain=os.getenv("ELASTIC_DOMAIN"),
    elastic_port=os.getenv("ELASTIC_PORT"),
    index='file_index'
)

guild_ids = [812818660141170748]


@bot.event
async def on_ready():
    """Occurs when the discord client is ready."""
    print(f'{bot.user} has connected to Discord!')


@slash.slash(
    name="all",
    description="Show all files",
    options=[
        create_option(
            name="dm",
            description="If `True`, I'll dm you what I find. \
                Otherwise, I'll send it to this channel",
            option_type=SlashCommandOptionType.BOOLEAN,
            required=False)],
    guild_ids=guild_ids)
async def _all(ctx, dm=False):
    files = await fall(ctx)
    if isinstance(files, str):
        await ctx.send(files, hidden=True)
        return

    if dm:
        await ctx.send(content="I'll dm you what I find", hidden=True)
        await send_files_as_message(ctx.author, files)
    else:
        await send_files_as_message(ctx, files)


@slash.slash(
    name="search",
    description="Search for files.",
    options=[
        create_option(
            name="filename",
            description="Even a partial name of your file will do :)",
            option_type=SlashCommandOptionType.STRING,
            required=True,
        ),
        create_option(
            name="dm",
            description="If `True`, I'll dm you what I find. \
                Otherwise, I'll send it to this channel",
            option_type=SlashCommandOptionType.BOOLEAN,
            required=False,
        )
    ],
    guild_ids=guild_ids)
async def _search(ctx, filename, dm=False):
    files = await fsearch(ctx, filename)
    if isinstance(files, str):
        await ctx.send(content=files, hidden=True)
        return
    if dm:
        # await ctx.send(content=f"I'll dm you what I find", hidden=True)
        await send_files_as_message(ctx.author, files)
    else:
        # await ctx.send(content=f"I'll send what I find in this channel",
        # hidden=True)
        await send_files_as_message(ctx, files)


@slash.slash(
    name="delete",
    description="Delete files AND messages",
    options=[
        create_option(
            name="filename",
            description="Even a partial name of your files will do :)",
            option_type=SlashCommandOptionType.STRING,
            required=True,
        )
    ],
    guild_ids=guild_ids)
async def _delete(ctx, filename):
    deleted_files = await fdelete(ctx, filename)
    if isinstance(deleted_files, str):
        await ctx.send(content=deleted_files, hidden=True)
        return
    await ctx.send(content=f"Deleted {' '.join(deleted_files)}", hidden=True)


@slash.slash(
    name="remove",
    description="Remove files from index \
        (These files will no longer be searchable!!)",
    options=[
        create_option(
            name="filename",
            description="Even a partial name of your files will do :)",
            option_type=SlashCommandOptionType.STRING,
            required=True,
        )],
    guild_ids=guild_ids)
async def _remove(ctx, filename):
    removed_files = await fremove(ctx, filename)
    if isinstance(removed_files, str):
        await ctx.send(content=removed_files, hidden=True)
        return
    await ctx.send(content=f"Removed {' '.join(removed_files)}", hidden=True)


@bot.command(name="fsearch", aliases=["fs", "search", "s"], pass_context=True)
async def search(ctx, filename):
    files = await fsearch(ctx, filename)
    if isinstance(files, str):
        await ctx.author.send(content=files, hidden=True)
        return
    await send_files_as_message(ctx, files)


@bot.command(name="all", aliases=["a"], pass_context=True)
async def all(ctx):
    files = await fall(ctx)
    if isinstance(files, str):
        await ctx.author.send(files)
        return
    await send_files_as_message(ctx.author, files)


@bot.command(name="delete", aliases=["del"], pass_context=True)
async def delete(ctx, arg):
    deleted_files = await fdelete(ctx, arg)
    if isinstance(deleted_files, str):
        await ctx.author.send(deleted_files)
        return
    await ctx.author.send("Deleted: " + ' '.join(deleted_files))


@bot.command(name="remove", aliases=["rm"], pass_context=True)
async def remove(ctx, arg):
    removed_files = await fremove(ctx, arg)
    if isinstance(removed_files, str):
        await ctx.author.send(removed_files)
        return
    await ctx.author.send("Removed: " + ' '.join(removed_files))


async def fremove(ctx, filename):
    author = ctx.author
    if not filename:
        return f"Couldn't process your query: `{filename}`"

    manageable_files = filter_messages_with_permissions(
        author,
        es_client.search(filename),
        discord.Permissions(read_message_history=True)
    )
    if not manageable_files:
        return f"I couldn't find any files related to `{filename}`"
    removed_files = []
    for file in manageable_files:
        es_client.delete_doc(file['_id'])
        removed_files.append(file['_source']['file_name'])
    return removed_files


async def fdelete(ctx, filename):
    author = ctx.author
    if not filename:
        return f"Couldn't process your query: `{filename}`"

    manageable_files = filter_messages_with_permissions(
        author,
        es_client.search(filename),
        discord.Permissions(read_message_history=True)
    )
    if not manageable_files:
        return f"I couldn't find any files related to `{filename}`"
    deleted_files = []
    for file in manageable_files:
        es_client.delete_doc(file['_id'])
        try:
            onii_chan = bot.get_channel(int(file['_source']['channel_id']))
            message = await onii_chan.fetch_message(file['_source']['message_id'])
            await message.delete()
            deleted_files.append(file['_source']['file_name'])
        except discord.Forbidden:
            continue
    return deleted_files


async def fall(ctx):
    author = ctx.author
    files = filter_messages_with_permissions(
        author,
        es_client.get_all_docs(),
        discord.Permissions(read_message_history=True)
    )
    if not files:
        return f"I couldn't find any files"
    return files


async def fsearch(ctx, filename):
    author = ctx.author
    if not filename:
        return f"Couldn't process your query: `{filename}`"

    files = filter_messages_with_permissions(
        author,
        es_client.search(filename),
        discord.Permissions(read_message_history=True)
    )
    if not files:
        return f"I couldn't find any files related to `{filename}`"
    return files


@bot.event
async def on_message(message: discord.Message):
    """Handles messages as they occur in the bot's channels.

    For attachments:
        Indexes any message attachments with ElasticSearch.

    For queries:
        Processes the appropriate queries.

    Args:
        message: A discord.Message that represents the newest message.
    """
    if message.author == bot.user:
        return
    await es_client.create_doc(message)
    await bot.process_commands(message)


@bot.event
async def on_raw_message_delete(payload):
    if payload.cached_message is None:
        onii_chan = bot.get_channel(payload.channel_id)

        if not onii_chan:
            return
        # Can you simply put the expressions for fetching the message
        # together here? Yes.
        # But could I bring myself to do it? Never.
        message = await onii_chan.fetch_message(payload.message_id)
    else:
        message = payload.cached_message
    for file in message.attachments:
        es_client.delete_doc(file.id)


def filter_messages_with_permissions(
        author: discord.User,
        files: List[Dict],
        perm: discord.Permissions) -> List[Dict]:
    """Finds the messages that the `author` can view

    Args:
        author: The discord.User querying for files
        files: A list of dicts returned from ElasticSearch.
        perm: The permission you're filtering with.

    Returns:
        A list of dicts of files from ElasticSearch that the author can view.
    """
    viewable_files = []
    for file in files:
        file_chan_id = int(file['_source']['channel_id'])
        file_message_chan = bot.get_channel(file_chan_id)
        if isinstance(file_message_chan, discord.DMChannel):
            continue
        authorperms = file_message_chan.permissions_for(author)
        # Question: What happens when a user is invited to a channel and has
        # the `read_messages` permission?
        # The user could only view messages posted *after* they were added.
        # If their query has images posted both before *and* after the user was
        # invited, what should we return?
        if authorperms >= perm:
            viewable_files.append(file)
    return viewable_files


async def send_files_as_message(author: discord.User or SlashContext,
                                files: List[Dict]):
    """Sends files to the author of the message

    Args:
        author: The author of the search query
        files: A list of dicts of files returned from ElasticSearch
    """
    file_buf = download(files)
    await author.send(content="Here's what I found:", files=file_buf)
    for buf in file_buf:
        buf.close()


def download(files: List[Dict]) -> List[discord.File]:
    """Downloads files from their urls (discord cdn)

    Args:
        files: A list of dicts of files from ElasticSearch.

    Returns:
        A list of discord.File objects of the files retrieved.
    """
    filebufs = []
    for idx, file in enumerate(files):
        url = file['_source']['url']
        response = requests.get(url, stream=True)
        if not response.ok:
            print(response)
        file_buf = BytesIO()
        for blk in response.iter_content(1024):
            if not blk:
                break
            file_buf.write(blk)
        file_buf.seek(0)
        filename = file['_source']['file_name']
        if len(files) > 1:
            ext = filename.rindex('.')
            filename = filename[:ext] + str(idx) + filename[ext:]
        filebufs.append(discord.File(file_buf, filename))
    return filebufs


bot.run(TOKEN)
