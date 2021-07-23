"""Main Bot Controller."""
from algolia_client import AlgoliaClient
from mongo_client import MgClient
from utils import PLZ_VERIFY, attachment_to_search_dict, download, CONTENT_TYPE_CHOICES
from bot_commands import fall, fdelete, fremove, fsearch, fclear
from config import CONFIG
import logging
from discord_slash.utils.manage_commands import create_option, create_choice
from discord_slash.model import SlashCommandOptionType
from discord_slash import SlashCommand, SlashContext
from discord.ext import commands, tasks
import discord
import datetime
from dateutil import parser
from typing import List, Dict
import glob


dlogger = logging.getLogger('discord')
dlogger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
handler.setFormatter(formatter)
dlogger.addHandler(handler)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
fh = logging.FileHandler('main.log', encoding='utf-8', mode='w')
fh.setFormatter(formatter)
logger.addHandler(fh)

bot = commands.Bot(command_prefix='fs!', intents=discord.Intents.all())
slash = SlashCommand(bot, sync_commands=True)

# es_client = ElasticSearchClient()
ag_client = AlgoliaClient()
mg_client = MgClient()

TOKEN = CONFIG.TEST_DISCORD_TOKEN
guild_ids = [int(CONFIG.GUILD_ID)]
if CONFIG.DB_NAME == "production":
    TOKEN = CONFIG.DISCORD_TOKEN
print(f'In {CONFIG.DB_NAME} mode')
owner = None


@bot.event
async def on_ready():
    """Occurs when the discord client is ready."""
    global owner
    appinfo = await bot.application_info()
    owner = appinfo.owner
    print(f'{bot.user} has connected to Discord!')
    print(f'{owner} is my owner!')
    print(f'Guild ids: {guild_ids}')


@slash.slash(
    name="clear",
    description="Clears all docs. Use this power carefully.",
    guild_ids=guild_ids
)
async def _clear(ctx: SlashContext):
    await ctx.defer()
    serv = ctx.channel
    if ctx.guild:
        serv = ctx.guild
    if serv.id not in guild_ids:
        ctx.send("Clear is too dangerous to be used...")
        return
    await fclear(ag_client, mg_client, serv.id)
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
    """
    Responds to `/all`. Tries to display all docs from the Search Client.

    Args:
        ctx: The SlashContext from which the command originated
        DM: A bool for whether to dm the author the results.
    """
    await ctx.defer()
    files = await fall(ctx, ag_client, bot)
    if isinstance(files, str):
        await ctx.send(files, hidden=True)
        return
    if not files:
        await ctx.send("Found no messages", hidden=True)
        return
    if dm:
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
    guild_ids=guild_ids if CONFIG.DB_NAME == "testing" else []
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
        before += datetime.timedelta(days=1) - datetime.timedelta(microseconds=1)
    if after is not None:
        after = parser.parse(after)
        after = datetime.datetime(*after.timetuple()[:3])
        after -= datetime.timedelta(microseconds=1)
    files = await fsearch(ctx=ctx,
                          filename=filename,
                          search_client=ag_client,
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
    guild_ids=guild_ids if CONFIG.DB_NAME == "testing" else []
)
async def _delete(ctx, filename):
    """
    Responds to `/delete`. Tries to remove docs related to a query from ElasticSearch and their respective discord messages.

    Args:
        ctx: The SlashContext from which the command originated
        filename: A str of the filename to query for.
    """
    await ctx.defer()
    deleted_files = await fdelete(ctx, filename, ag_client, mg_client, bot)
    if isinstance(deleted_files, str):
        await ctx.send(content=deleted_files, hidden=True)
        return
    await ctx.send(content=f"Deleted {' '.join(deleted_files)}", hidden=True)


@slash.slash(
    name="remove",
    description="Remove files from index (These files will no longer be searchable!!)",
    options=[
        create_option(
            name="filename",
            description="Even a partial name of your files will do :)",
            option_type=SlashCommandOptionType.STRING,
            required=True,
        )],
    guild_ids=guild_ids if CONFIG.DB_NAME == "testing" else []
)
async def _remove(ctx: SlashContext, filename: str):
    """
    Responds to `/remove`. Tries to remove docs related to a query from ElasticSearch.

    Args:
        ctx: The SlashContext from which the command originated
        filename: A str of the filename to query for.
    """
    await ctx.defer()
    removed_files = await fremove(ctx, filename, ag_client, mg_client, bot)
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
    files = await fsearch(ctx, filename, ag_client, bot)
    if isinstance(files, str):
        await ctx.author.send(content=files)
        return
    await send_files_as_message(ctx, files)


@bot.command(name="clear", aliases=["c"], pass_context=True)
async def clear(ctx: commands.Context):
    """Clear the index associated with the current id."""
    serv = ctx.channel
    if ctx.guild:
        serv = ctx.guild
    if serv.id not in guild_ids:
        ctx.send("Clear is too dangerous to be used...")
        return
    if ctx.message.guild is not None:
        await fclear(ag_client, mg_client, ctx.message.guild.id)
    else:
        await fclear(ag_client, mg_client, ctx.message.channel.id)


@bot.command(name="all", aliases=["a"], pass_context=True)
async def all_docs(ctx: commands.Context):
    """
    Display all docs from ElasticSearch.

    Args:
        ctx: The commands.Context from which the command originated
    """
    serv = ctx.channel
    if ctx.guild:
        serv = ctx.guild
    if serv.id not in guild_ids:
        ctx.send("All is too spammy to be used...")
        return
    files = await fall(ctx, ag_client, bot)
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
    deleted_files = await fdelete(ctx, filename, ag_client, mg_client, bot)
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
    removed_files = await fremove(ctx, filename, ag_client, mg_client, bot)
    if isinstance(removed_files, str):
        await ctx.author.send(removed_files)
        return
    await ctx.author.send("Removed: " + ' '.join(removed_files))


@bot.event
async def on_slash_command(ctx: SlashContext):
    """Attempt to create an index for a channel on each command."""
    serv = ctx.channel
    if ctx.guild_id is not None:
        serv = ctx.guild
    await mg_client.add_server(serv)


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
    serv = message.channel
    if message.guild is not None:
        serv = message.guild
    await mg_client.add_server(serv)
    for file in message.attachments:
        meta_dict = attachment_to_search_dict(message, file)
        await ag_client.create_doc(meta_dict, serv.id, message.author.name + "#" + message.author.discriminator)
        saved_files = await mg_client.add_file(message)
        # if saved_files:
        # await message.channel.send(f"Saved {len(message.attachments)}
        # file{'s' if len(message.attachments) > 1 else ''}")

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
        onii_chan_id = message.channel.id
        if message.guild is not None:
            onii_chan_id = message.guild.id
    files = await ag_client.search(payload.message_id, onii_chan_id)
    await ag_client.remove_doc([file['objectID'] for file in files], onii_chan_id, "bot_deletion")


@bot.event
async def on_guild_join(guild: discord.Guild):
    """
    Log guild joins.

    Args:
        guild: The discord.Guild that the bot just joined
    """
    await mg_client.add_server(guild)


@bot.event
async def on_guild_remove(guild: discord.Guild):
    """
    Log guild joins.

    Args:
        guild: The discord.Guild that the bot just joined
    """
    await mg_client.remove_server(guild.id)
    await mg_client.remove_server_docs(guild.id)
    await ag_client.clear(guild.id)


@bot.event
async def on_command_error(ctx, e):
    """Command Error Handler."""
    await ctx.author.send(f"""I couldn't understand that query. All I see is `{e}`. If there was an issue in your \
query, please try again. If you think there's an issue with the bot, please message `{owner}`!""")
    if owner:
        await owner.send(f"{type(e)}\n{e}")


@tasks.loop(hours=24)
async def clear_irrelevant_docs():
    """Run a simple cleaner every 24 hours."""
    ack, ok = await mg_client.delete_files_from_inactive_servers()
    if not ok:
        logger.error("Deleted every element in the collection, restoring the database now...")
        snaps = sorted(glob.glob(f"{CONFIG.DB_NAME}_files/*"), reverse=True)[0]
        await mg_client.load_from_snapshot(snaps)
        logger.debug("Database restored!")


async def send_files_as_message(author: discord.User or SlashContext,
                                files: List[Dict]):
    """
    Send files to the author of the message.

    Args:
        author: The author or SlashContext of the search query
        files: A list of dicts of files returned from ElasticSearch
    """
    async for file in download(files, mg_client):
        await author.send(file=file)
        file.close()

bot.run(TOKEN)
