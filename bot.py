import os
from pathlib import Path
from typing import List, Dict

from commands import fall, fdelete, fremove, fsearch
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option

from utils import download
from elasticsearch_conn import ElasticSearchConnector


load_dotenv(dotenv_path=Path('.') / '.env')

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
async def _all(ctx: SlashContext, dm: bool = False):
    """Responds to `/all`. Tries to display all docs from ElasticSearch.

    Args:
        ctx: The SlashContext from which the command originated
        dm: A bool for whether to dm the author the results.
    """
    files = await fall(ctx, es_client, bot)
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
    """Responds to `/search`. Tries to display docs related to
    a query from ElasticSearch.

    Args:
        ctx: The SlashContext from which the command originated
        filename: A str of the filename to query for.
        dm: A bool for whether to dm the author the results.
    """
    files = await fsearch(ctx, filename, es_client, bot)
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
    """Responds to `/delete`. Tries to remove docs related to
    a query from ElasticSearch and their respective discord messages.

    Args:
        ctx: The SlashContext from which the command originated
        filename: A str of the filename to query for.
    """
    deleted_files = await fdelete(ctx, filename, es_client, bot)
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
async def _remove(ctx: SlashContext, filename: str):
    """Responds to `/remove`. Tries to remove docs related to
    a query from ElasticSearch.

    Args:
        ctx: The SlashContext from which the command originated
        filename: A str of the filename to query for.
    """
    removed_files = await fremove(ctx, filename, es_client, bot)
    if isinstance(removed_files, str):
        await ctx.send(content=removed_files, hidden=True)
        return
    await ctx.send(content=f"Removed {' '.join(removed_files)}", hidden=True)


@bot.command(name="fsearch", aliases=["fs", "search", "s"], pass_context=True)
async def search(ctx: commands.Context, filename: str):
    """Tries to display docs related to a query from ElasticSearch.

    Args:
        ctx: The commands.Context from which the command originated
        filename: A str of the filename to query for.
    """
    files = await fsearch(ctx, filename, es_client, bot)
    if isinstance(files, str):
        await ctx.author.send(content=files, hidden=True)
        return
    await send_files_as_message(ctx, files)


@bot.command(name="all", aliases=["a"], pass_context=True)
async def all_files(ctx: commands.Context):
    """Displays all docs from ElasticSearch.

    Args:
        ctx: The commands.Context from which the command originated
    """
    files = await fall(ctx, es_client, bot)
    if isinstance(files, str):
        await ctx.author.send(files)
        return
    await send_files_as_message(ctx.author, files)


@bot.command(name="delete", aliases=["del"], pass_context=True)
async def delete(ctx: commands.Context, filename: str):
    """Tries to delete docs related to the given filename from ElasticSearch
    and their respective messages.

    Args:
        ctx: The commands.Context from which the command originated
        filename: A str of the filename to query for
    """
    deleted_files = await fdelete(ctx, filename, es_client, bot)
    if isinstance(deleted_files, str):
        await ctx.author.send(deleted_files)
        return
    await ctx.author.send("Deleted: " + ' '.join(deleted_files))


@bot.command(name="remove", aliases=["rm"], pass_context=True)
async def remove(ctx, filename):
    """Tries to remove docs related to the given filename from ElasticSearch.

    Args:
        ctx: The commands.Context from which the command originated
        filename: A str of the filename to query for
    """
    removed_files = await fremove(ctx, filename, es_client, bot)
    if isinstance(removed_files, str):
        await ctx.author.send(removed_files)
        return
    await ctx.author.send("Removed: " + ' '.join(removed_files))


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
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    """Handles message deletion. Removes the respective documents from the index.

    Args:
        payload: A discord.RawMessageDeleteEvent event.
    """
    if payload.cached_message is None:
        onii_chan_id = payload.channel_id
        onii_chan = bot.get_channel(onii_chan_id)

        if not onii_chan:
            return
        message = await onii_chan.fetch_message(payload.message_id)
    else:
        message = payload.cached_message
    for file in message.attachments:
        es_client.delete_doc(file.id)


async def send_files_as_message(author: discord.User or SlashContext,
                                files: List[Dict]):
    """Sends files to the author of the message
    Args:
        author: The author or SlashContext of the search query
        files: A list of dicts of files returned from ElasticSearch
    """
    file_buf = download(files)
    await author.send(content="Here's what I found:", files=file_buf)
    for buf in file_buf:
        buf.close()


bot.run(TOKEN)
