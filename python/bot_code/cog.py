"""Cog class."""
from cryptography.fernet import Fernet
from functools import wraps
from .security.SymmetricMessageEncryptor import SymmetricMessageEncryptor
from .search import AsyncSearchClient
from .search.discord_searcher import DiscordSearcher
from .database.async_data_client import AsyncDataClient
from .database.file_data_client import FileDataClient
from .models.query import Query
from .config import CONFIG
import logging
import discord
from discord import app_commands
from discord.ext import commands, tasks
from .utils import search_opts, CONTENT_TYPE_CHOICES
from .bot_commands import fdelete, fsearch
from .export_template import generate_script
import datetime
from dateutil import parser
import glob
from typing import List, Tuple, Union
import io
import re
import hashlib
from .views.file_view import FileView
from .views.help_view import HelpEmbed
from .views.file_embed import FileEmbed
from .discord_utils import update_server_count
from .search.search_models import SearchResults

guild_ids = []
if getattr(CONFIG, "GUILD_ID", None):
    guild_ids = [discord.Object(id=int(CONFIG.GUILD_ID))]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
fh = logging.FileHandler('main.log', encoding='utf-8', mode='w')
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


class Haystackfs(commands.Cog):
    """Main class for the bot."""

    def __init__(self, guild_ids: List, bot,
                 search_client: AsyncSearchClient,
                 db_client: AsyncDataClient,
                 sme: SymmetricMessageEncryptor) -> None:
        """Instantiate the bot."""
        self.bot = bot
        self.guild_ids = guild_ids
        self.owner = None
        self.search_client = search_client
        self.db_client = db_client
        self.sme = sme

    @commands.Cog.listener()
    async def on_ready(self):
        """Occurs when the discord client is ready."""
        appinfo = await self.bot.application_info()
        self.owner = appinfo.owner
        print(f'{self.bot.user} has connected to Discord!')
        print(f'{self.owner} is my owner!')
        print(f'Guild ids: {self.guild_ids}')

        for guild in self.bot.guilds:
            if guild.id == guild_ids[0].id:
                self.home_guild = guild
                break
        await update_server_count(self.home_guild, len(self.bot.guilds))

    @app_commands.command(
        name="help",
        description="A help command",
        # options=[dm_option],
        # guild_ids=guild_ids if getattr(CONFIG, "DB_NAME", "production") == "testing" else []
    )
    @app_commands.describe(dm="If true, I'll dm results to you.")
    async def slash_help(self, interaction: discord.Interaction, dm: bool = False) -> None:
        """
        Responds to /help. Displays a help command with commands and search options.

        Args:
            interaction: The context from which the command was issued
            dm: Whether to display the command only to the author
        """
        await interaction.response.defer(ephemeral=dm)
        name = self.bot.user.name
        avatar_url = self.bot.user.display_avatar.url

        await interaction.followup.send(embed=HelpEmbed(name=name, avatar_url=avatar_url), ephemeral=dm)

    async def locate(self, interaction: discord.Interaction, query: Query) -> Tuple[Union[discord.Interaction, discord.member.Member, discord.user.ClientUser], SearchResults]:
        """
        Turn arguments into a search and return the files.

        Args:
            interaction: The SlashContext from which the command originated
            query: The user query

        Returns a destination that has a .send method, and a list of files.
        """

        if query.before:
            before = parser.parse(query.before)
            before = datetime.datetime(*before.timetuple()[:3])
            before += datetime.timedelta(days=1) - datetime.timedelta(microseconds=1)
            query.before = before

        if query.after:
            after = parser.parse(query.after)
            after = datetime.datetime(*after.timetuple()[:3])
            after -= datetime.timedelta(microseconds=1)
            query.after = after

        if query.channel and interaction.guild is not None:
            if not query.channel.permissions_for(interaction.guild.me).read_message_history:
                await interaction.send(f"I can't read messages in {query.channel.name}! Please give me `read_message_history` permissions for {query.channel.name}", ephemeral=query.dm)
                return interaction, SearchResults(message=f"I can't read messages in {query.channel.name}! Please give me `read_message_history` permissions for {query.channel.name}")
        files = await fsearch(interaction=interaction, search_client=self.search_client, query=query)

        if files.message:
            await interaction.followup.send(content=files.message, ephemeral=True)
            return interaction, files
        recipient = interaction.followup
        if query.dm:
            recipient = interaction.user
            await interaction.followup.send("DM'ing your files...", ephemeral=True)
        return recipient, files

    @app_commands.command(name="search", description="Search for your files!")
    @app_commands.describe(**search_opts)
    @app_commands.choices(filetype=CONTENT_TYPE_CHOICES)
    async def slash_search(self, interaction: discord.Interaction, filename: str = None,
                           filetype: str = None, custom_filetype: str = None,
                           author: discord.User = None, channel: discord.TextChannel = None, content: str = None,
                           after: str = None, before: str = None, dm: bool = False):
        """Responds to `/search`. Tries to display docs related to a query."""
        await interaction.response.defer(ephemeral=dm)
        query = Query(
            filename=filename,
            filetype=filetype,
            custom_filetype=custom_filetype,
            author=author,
            channel=channel,
            content=content,
            after=after,
            before=before,
            dm=dm
        )
        await self.db_client.log_command(interaction, 'search', query)

        recipient, files = await self.locate(interaction=interaction, query=query)
        if files.message:
            await interaction.followup.send(content=files.message, ephemeral=True)
        else:
            await self.send_files_as_message(recipient, files)

    @app_commands.command(name="export",
                          description="Get a Python export script to download the files returned in a search to your computer.")
    @app_commands.describe(**search_opts)
    @app_commands.choices(filetype=CONTENT_TYPE_CHOICES)
    async def slash_export(self, interaction: discord.Interaction, filename: str = None,
                           filetype: str = None, custom_filetype: str = None,
                           author: discord.User = None, channel: discord.TextChannel = None, content: str = None,
                           after: str = None, before: str = None, dm: bool = None):
        """Responds to `/export`. Tries get a download script for all files related to a query."""
        await interaction.response.defer(ephemeral=dm)
        query = Query(
            filename=filename,
            filetype=filetype,
            custom_filetype=custom_filetype,
            author=author,
            channel=channel,
            content=content,
            after=after,
            before=before,
            dm=dm
        )
        await self.db_client.log_command(interaction, 'export', query)
        recipient, files = await self.locate(interaction=interaction, query=query)
        if not files.files:
            return

        # So file names are maximally compatible.
        def sanitize(s, default): return re.sub(r"[^A-Za-z0-9'\-\_ ]", "", s).rstrip() or default

        # Restrict to channels that the search returns files for. This is so that the
        # script does not leak the full server channel list every export. This mapping
        # is required so the export script can save files in directories named by the channels.
        needed_ids = set(f.channel_id for f in files.files)
        if interaction.guild is None:
            chan = interaction.channel
            channels = {str(chan.id): sanitize(chan, str(chan.id))}
            guild_name = sanitize(chan.name, "export")
        else:
            channels = {
                str(c.id): sanitize(c.name, str(c.id))
                for c in interaction.guild.channels
                if c.id in needed_ids
            }
            guild_name = sanitize(interaction.guild.name, "export")

        # This is so that if one is running multiple exports in a server,
        # they don't get export(1).py etc.
        unique_suffix = hashlib.sha256(bytes(str(sorted(f.url for f in files.files)), "utf-8")).hexdigest()[:5]
        filename = f"export_{guild_name}_{unique_suffix}.py"
        with io.StringIO(generate_script(guild_name, files.files, channels)) as export_script:
            await recipient.send(
                f"Found {len(files.files)} file(s). Run this script to download them.",
                file=discord.File(export_script, filename=filename))

    @app_commands.command(name="delete",
                          description="Delete files AND their respective messages")
    @app_commands.describe(**search_opts)
    @app_commands.choices(filetype=CONTENT_TYPE_CHOICES)
    async def slash_delete(self, interaction: discord.Interaction, filename: str = None,
                           filetype: str = None, custom_filetype: str = None,
                           author: discord.User = None, channel: discord.TextChannel = None, content: str = None,
                           after: str = None, before: str = None, dm: bool = None):
        """Responds to `/delete`. Tries to remove docs related to a query and their respective discord messages."""
        await interaction.response.defer(ephemeral=True)
        query = Query(
            filename=filename,
            filetype=filetype,
            custom_filetype=custom_filetype,
            author=author,
            channel=channel,
            content=content,
            after=after,
            before=before,
            dm=dm
        )
        await self.db_client.log_command(interaction, 'delete', query)
        deleted_files = await fdelete(interaction, self.search_client, self.bot, query)
        if isinstance(deleted_files, str):
            await interaction.followup.send(content=deleted_files, ephemeral=True)
            return
        await interaction.followup.send(content=f"Deleted {' '.join(deleted_files)}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Handle messages as they occur in the bot's channels.

        For attachments:
            Indexes any message attachments with ElasticSearch.
        For queries:
            Processes the appropriate queries.

        Args:
            message: A discord.Message that represents the newest message.
        """
        if message.author == self.bot.user:
            return
        # Only track files and servers that have files uploaded to them
        if message.attachments:
            message.content = self.sme.encrypt(message.content)
            await self.search_client.create_doc(message)
            await self.db_client.add_file(message)
        await self.bot.process_commands(message)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        """
        Remove respective documents from the database when they're deleted.

        Args:
            payload: A discord.RawMessageDeleteEvent event.
        """
        await self.db_client.remove_file([payload.message_id], field="message_id")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """
        Log guild joins.

        Args:
            guild: The discord.Guild that the bot just joined
        """
        await update_server_count(self.home_guild, len(self.bot.guilds))
        await self.db_client.add_server(guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """
        Log guild joins.

        Args:
            guild: The discord.Guild that the bot just joined
        """
        await update_server_count(self.home_guild, len(self.bot.guilds))
        await self.db_client.remove_server(guild.id)
        await self.db_client.remove_server_docs(guild.id)
        await self.search_client.clear(guild.id)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, e):
        """Command Error Handler."""
        if self.owner:
            await self.owner.send(f"{vars(ctx)}\n{type(e)}\n{e}")

    @tasks.loop(hours=24)
    async def clear_irrelevant_docs(self):
        """Run a simple cleaner every 24 hours."""
        ack, ok = await self.db_client.delete_files_from_inactive_servers()
        if not ok:
            logger.error("Deleted every element in the collection, restoring the database now...")
            snaps = sorted(glob.glob(f"{getattr(CONFIG, 'DB_NAME', 'normal')}_files/*"), reverse=True)[0]
            await self.db_client.load_from_snapshot(snaps)
            logger.debug("Database restored!")

    @tasks.loop(hours=24)
    async def clear_messages(self):
        """Run a simple cleaner every 24 hours."""
        await self.db_client.clear_message_content()

    async def send_files_as_message(self, recipient, files: SearchResults):
        """
        Send files as a message to ctx.

        Args:
            ctx: The originating context.
            files: The files to send to the context.
        """
        name = self.bot.user.name
        avatar_url = self.bot.user.display_avatar.url
        view = FileView(files)
        embed = FileEmbed(files, name=name, avatar_url=avatar_url)
        message = f"Found {files.files[0].filename} {'and more...' if len(files.files) > 1 else ''}"
        if len(message) > 100:
            message = message[:96] + '...'
        await recipient.send(message, embed=embed, view=view)


async def setup(bot):
    """
    Set up the bot.

    Args:
        bot: The discord bot.
    """
    db_name = getattr(CONFIG, "DB_NAME", "normal")
    print(f'In {db_name} mode')
    searcher = DiscordSearcher()
    command_client = FileDataClient(db_name=db_name)
    sme = SymmetricMessageEncryptor(Fernet, CONFIG)
    await bot.add_cog(Haystackfs(guild_ids, bot, searcher, command_client, sme))
