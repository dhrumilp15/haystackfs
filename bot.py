"""Main Bot Controller."""
from typing import List, Dict
from dateutil import parser
import datetime

import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option, create_choice
import logging
import sys


from config import CONFIG
from bot_commands import fall, fdelete, fremove, fsearch, fclear
from utils import download, CONTENT_TYPE_CHOICES
from elasticsearch_client import ElasticSearchClient
from mongo_client import MgClient

logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s: %(levelname)s:%(message)s',
    filename='out.log',
    level=logging.DEBUG)

TOKEN = CONFIG['TEST_DISCORD_TOKEN']

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
slash = SlashCommand(bot, sync_commands=True)

es_client = ElasticSearchClient()
mongo_client = MgClient()

guild_ids = [int(CONFIG["GUILD_ID"])]


@bot.event
async def on_ready():
    """Occurs when the discord client is ready."""
    print(f'{bot.user} has connected to Discord!')


@slash.slash(
    name="clear",
    description="Clears all docs. Use this power carefully.",
    guild_ids=guild_ids
)
async def _clear(ctx: SlashContext):
    await ctx.defer()
    if ctx.guild_id is None:
        await fclear(es_client, ctx.channel_id)
    else:
        await fclear(es_client, ctx.guild_id)
    await ctx.send(content="Index cleared", hidden=True)


@slash.slash(
    name="all",
    description="Show all files",
    options=[
        create_option(
            name="dm",
            description="Whether I should dm you what I find",
            option_type=SlashCommandOptionType.BOOLEAN,
            required=False)],
    guild_ids=guild_ids
)
async def _all(ctx: SlashContext, dm: bool = False):
    """Responds to `/all`. Tries to display all docs from ElasticSearch.

    Args:
        ctx: The SlashContext from which the command originated
        DM: A bool for whether to dm the author the results.
    """
    await ctx.defer()
    files = await fall(ctx, es_client, bot)
    if isinstance(files, str):
        await ctx.send(files, hidden=True)
        return

    await ctx.send(content="Searching...", hidden=True)
    if dm:
        await send_files_as_message(ctx.author, files)
    else:
        await send_files_as_message(ctx.channel, files)


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
            name="filetype",
            description="You can choose a filetype here. Use `custom filetype` to specify a different one",
            option_type=SlashCommandOptionType.STRING,
            required=False,
            choices=sorted([create_choice(**tup)
                            for tup in CONTENT_TYPE_CHOICES[:-1]], key=lambda val: val["name"]) + [create_choice(**(CONTENT_TYPE_CHOICES[-1]))]
        ),
        create_option(
            name="custom_filetype",
            description="Searches for files of a custom file type",
            option_type=SlashCommandOptionType.STRING,
            required=False,
        ),
        create_option(
            name="author",
            description="Searches for files uploaded by a user",
            option_type=SlashCommandOptionType.USER,
            required=False
        ),
        create_option(
            name="channel",
            description="Searches for files in a channel",
            option_type=SlashCommandOptionType.CHANNEL,
            required=False
        ),
        create_option(
            name="content",
            description="Search for files in messages by message content",
            option_type=SlashCommandOptionType.STRING,
            required=False
        ),
        create_option(
            name="after",
            description="Search for files after a date. \
                Use the `before` option to specify a range of dates",
            option_type=SlashCommandOptionType.STRING,
            required=False
        ),
        create_option(
            name="before",
            description="Search for files before a date. \
                Use the `after` option to specify a range of dates",
            option_type=SlashCommandOptionType.STRING,
            required=False
        ),
        create_option(
            name="dm",
            description="If `True`, I'll dm you what I find. \
                Otherwise, I'll send it to this channel",
            option_type=SlashCommandOptionType.BOOLEAN,
            required=False,
        ),
    ],
    guild_ids=guild_ids
)
async def _search(ctx: SlashContext,
                  filename: str,
                  filetype: str = None,
                  custom_filetype: str = None,
                  author: discord.User = None,
                  channel: discord.channel = None,
                  content: str = None,
                  after: str = None,
                  before: str = None,
                  dm: bool = False):
    """
    Responds to `/search`. Tries to display docs related to a query from ElasticSearch.

    Args:
        ctx: The SlashContext from which the command originated
        filename: A str of the filename to query for.
        DM: A bool for whether to dm the author the results.
    """
    await ctx.defer()

    if filetype == "OTHER" and custom_filetype is None:
        await ctx.send(f"You specified a custom filetype but didn't provide one!")
        return

    if filetype is not None and custom_filetype is not None:
        filetype = custom_filetype

    if before is not None:
        before = parser.parse(before)
        # Long way to do it but I'm not sure how else to do this
        before = datetime.datetime(*before.timetuple()[:3])
        before += datetime.timedelta(days=1) - \
            datetime.timedelta(microseconds=1)
    if after is not None:
        after = parser.parse(after)
        after = datetime.datetime(*after.timetuple()[:3])
        after -= datetime.timedelta(microseconds=1)

    files = await fsearch(ctx=ctx,
                          filename=filename,
                          es_client=es_client,
                          bot=bot,
                          mimetype=filetype,
                          author=author,
                          content=content,
                          channel=channel,
                          after=after,
                          before=before)
    if isinstance(files, str):
        await ctx.send(content=files, hidden=True)
        return

    if dm:
        await ctx.send(content="I'll dm you what I find", hidden=True)
        await send_files_as_message(ctx.author, files)
    else:
        await send_files_as_message(ctx, files)


@slash.slash(
    name="delete",
    description="Delete files AND their respective messages",
    options=[
        create_option(
            name="filename",
            description="Even a partial name of your files will do :)",
            option_type=SlashCommandOptionType.STRING,
            required=True,
        )
    ],
    guild_ids=guild_ids
)
async def _delete(ctx, filename):
    """
    Responds to `/delete`. Tries to remove docs related to a query from ElasticSearch and their respective discord messages.

    Args:
        ctx: The SlashContext from which the command originated
        filename: A str of the filename to query for.
    """
    await ctx.defer()
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
    guild_ids=guild_ids
)
async def _remove(ctx: SlashContext, filename: str):
    """
    Responds to `/remove`. Tries to remove docs related to a query from ElasticSearch.

    Args:
        ctx: The SlashContext from which the command originated
        filename: A str of the filename to query for.
    """
    await ctx.defer()
    removed_files = await fremove(ctx, filename, es_client, bot)
    if isinstance(removed_files, str):
        await ctx.send(content=removed_files, hidden=True)
        return
    await ctx.send(content=f"Removed {' '.join(removed_files)}", hidden=True)


@bot.command(name="fsearch", aliases=["fs", "search", "s"], pass_context=True)
async def search(ctx: commands.Context, filename: str):
    """
    Display docs related to a query from ElasticSearch.

    Args:
        ctx: The commands.Context from which the command originated
        filename: A str of the filename to query for.
    """
    files = await fsearch(ctx, filename, es_client, bot)
    if isinstance(files, str):
        await ctx.author.send(content=files, hidden=True)
        return
    await send_files_as_message(ctx, files)


@bot.command(name="clear", aliases=["c"], pass_context=True)
async def clear(ctx: commands.Context):
    """Clear the index associated with the current id."""
    if ctx.message.guild is not None:
        await fclear(es_client, ctx.message.guild.id)
    else:
        await fclear(es_client, ctx.message.channel.id)


@bot.command(name="all", aliases=["a"], pass_context=True)
async def all_docs(ctx: commands.Context):
    """
    Display all docs from ElasticSearch.

    Args:
        ctx: The commands.Context from which the command originated
    """
    files = await fall(ctx, es_client, bot)
    if isinstance(files, str):
        await ctx.send(files)
        return
    await ctx.send("I found these:")
    await send_files_as_message(ctx, files)


@bot.command(name="delete", aliases=["del"], pass_context=True)
async def delete(ctx: commands.Context, filename: str):
    """
    Delete docs related to the given filename from ElasticSearch and their respective messages.

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
    """
    Remove docs related to the given filename from ElasticSearch.

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
async def on_slash_command(ctx: SlashContext):
    """Attempt to create an index for a channel on each command."""
    if ctx.guild_id is None:
        es_client.create_index(ctx.channel_id)
        res = mongo_client.add_server(ctx.channel)
    else:
        es_client.create_index(ctx.guild_id)
        res = mongo_client.add_server(ctx.guild)


@bot.event
async def on_message(message: discord.Message):
    """
    Handle messages as they occur in the bot's channels.

    For attachments:
        Indexes any message attachments with ElasticSearch.
    For queries:
        Processes the appropriate queries.
    Args:
        message: A discord.Message that represents the newest message.
    """
    if message.author == bot.user:
        return
    # Only track files and servers that have files uploaded to them
    serv_id = message.channel.id
    if message.guild is not None:
        serv_id = message.guild.id
    es_client.create_index(serv_id)
    es_client.create_doc(message, serv_id)
    res = mongo_client.add_server(
        message.guild if message.guild is not None else message.channel)
    if message.attachments:
        res = mongo_client.add_file(message)
        await message.channel.send(f"Saved {res} image{'s' if res > 1 else ''}")
        # es_client.make_snapshot()

    await bot.process_commands(message)


@bot.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    """
    Handle message deletion. Removes the respective documents from the index.

    This is also called when we delete messages in `_delete()`, but that's not
    a problem since we only remove docs from indices if they exist.

    Args:
        payload: A discord.RawMessageDeleteEvent event.
    """
    if payload.cached_message is None:
        onii_chan_id = payload.channel_id
    else:
        message = payload.cached_message
        # if the message is cached, we'll know whether the author is a bot user
        if message.author == bot.user:
            return
        if isinstance(
                message,
                discord.DMChannel) or isinstance(
                message,
                discord.GroupChannel):
            onii_chan_id = message.channel.id
        else:
            onii_chan_id = message.guild.id
    files = es_client.search_message_id(
        message_id=payload.message_id, index=onii_chan_id)

    for file in files:
        es_client.delete_doc(file['_id'], onii_chan_id)


# @bot.event
# async def on_guild_join(guild: discord.Guild):
#     """Log guild joins

#     Args:
#         guild: The discord.Guild that the bot just joined
#     """
#     with open("guild_joins.log", 'a') as fp:
#         fp.write(f"Joined {guild.name}\n")


async def send_files_as_message(author: discord.User or SlashContext,
                                files: List[Dict]):
    """
    Send files to the author of the message.

    Args:
        author: The author or SlashContext of the search query
        files: A list of dicts of files returned from ElasticSearch
    """
    file_buf = download(files)
    for file in file_buf:
        await author.send(file=file)
    for file in file_buf:
        file.close()

bot.run(TOKEN)
