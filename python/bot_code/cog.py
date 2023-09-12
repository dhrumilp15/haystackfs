"""Cog class."""
from .search.discord_searcher import DiscordSearcher
from .database.file_data_client import FileDataClient
from .models.query import Query
from .bot_secrets import GUILD_ID, DB_NAME
import logging
import discord
from discord import app_commands
from discord.ext import commands
from .utils import search_opts, CONTENT_TYPE_CHOICES
from .bot_commands import fdelete, fsearch
from .export_template import generate_script
from typing import List, Tuple, Union
import io
import re
import hashlib
from .views.file_view import FileView
from .views.help_view import HelpEmbed
from .views.file_embed import FileEmbed
from .discord_utils import update_server_count
from .search.search_models import SearchResults
from .messages import (
    INSUFFICIENT_BOT_PERMISSIONS,
    EXPORT_COMMAND_DESCRIPTION,
    SEARCH_RESULTS_FOUND
)

guild_ids = [] if not GUILD_ID else [GUILD_ID]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
fh = logging.FileHandler('../logs/main.log', encoding='utf-8', mode='w')
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


class Haystackfs(commands.Cog):
    """Main class for the bot."""

    def __init__(self, guild_ids: List, bot,
                 search_client,
                 db_client) -> None:
        """Instantiate the bot."""
        self.bot = bot
        self.guild_ids = guild_ids
        self.owner = None
        self.search_client = search_client
        self.db_client = db_client

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
        print(f"home guild id: {self.home_guild}")
        # await update_server_count(self.home_guild, len(self.bot.guilds))
        # print("updated server count")

    @app_commands.command(name="help",description="A help command")
    @app_commands.describe(dm="If true, I'll dm results to you.")
    async def slash_help(self, interaction: discord.Interaction, dm: bool = False) -> None:
        """Respond to /help. Display a help command with commands and search options."""
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
        if query.channel and interaction.guild is not None:
            if not query.channel.permissions_for(interaction.guild.me).read_message_history:
                return interaction, SearchResults(
                    message=INSUFFICIENT_BOT_PERMISSIONS.format(query.channel.name, query.channel.name)
                )
        search_results = await fsearch(interaction=interaction, search_client=self.search_client, query=query)

        if search_results.message:
            return interaction, search_results
        recipient = interaction.followup
        if query.dm:
            recipient = interaction.user
            await interaction.followup.send("DM'ing your files...", ephemeral=True)
        return recipient, search_results

    @app_commands.command(name="search", description="Search for your files!")
    @app_commands.describe(**search_opts)
    @app_commands.choices(filetype=CONTENT_TYPE_CHOICES)
    async def slash_search(self, interaction: discord.Interaction, filename: str = None,
                           filetype: str = None, custom_filetype: str = None,
                           author: discord.User = None, channel: discord.TextChannel = None, content: str = None,
                           after: str = None, before: str = None, dm: bool = False):
        """Responds to `/search`. Tries to display docs that match a query."""
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

        recipient, search_results = await self.locate(interaction=interaction, query=query)
        if search_results.message:
            await interaction.followup.send(content=search_results.message, ephemeral=dm)
        else:
            await self.send_files_as_message(recipient, search_results)

    @app_commands.command(name="export", description=EXPORT_COMMAND_DESCRIPTION)
    @app_commands.describe(**search_opts)
    @app_commands.choices(filetype=CONTENT_TYPE_CHOICES)
    async def slash_export(self, interaction: discord.Interaction, filename: str = None,
                           filetype: str = None, custom_filetype: str = None,
                           author: discord.User = None, channel: discord.TextChannel = None, content: str = None,
                           after: str = None, before: str = None, dm: bool = None):
        """Responds to `/export`. Builds a download script for all files matching a query."""
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
        recipient, search_results = await self.locate(interaction=interaction, query=query)
        if search_results.message:
            await interaction.followup.send(content=search_results.message, ephemeral=dm)
            return

        # So file names are maximally compatible.
        def sanitize(s, default): return re.sub(r"[^A-Za-z0-9'\-\_ ]", "", s).rstrip() or default

        # Restrict to channels that the search returns files for. This is so that the
        # script does not leak the full server channel list every export. This mapping
        # is required so the export script can save files in directories named by the channels.
        needed_ids = set(f.channel_id for f in search_results.files)
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
        unique_suffix = hashlib.sha256(bytes(str(sorted(f.url for f in search_results.files)), "utf-8")).hexdigest()[:5]
        filename = f"export_{guild_name}_{unique_suffix}.py"
        with io.StringIO(generate_script(guild_name, search_results.files, channels)) as export_script:
            await recipient.send(
                f"Found {len(search_results.files)} file(s). Run this script to download them.",
                file=discord.File(export_script, filename=filename))

    @app_commands.command(name="delete", description="Delete files AND their respective messages")
    @app_commands.describe(**search_opts)
    @app_commands.choices(filetype=CONTENT_TYPE_CHOICES)
    async def slash_delete(self, interaction: discord.Interaction, filename: str = None,
                           filetype: str = None, custom_filetype: str = None,
                           author: discord.User = None, channel: discord.TextChannel = None, content: str = None,
                           after: str = None, before: str = None, dm: bool = None):
        """Respond to `/delete`. Remove docs matching a query and their respective discord messages."""
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
        await self.bot.process_commands(message)

    @commands.Cog.listener()
    async def on_guild_join(self):
        """Log guild joins."""
        await update_server_count(self.home_guild, len(self.bot.guilds))

    @commands.Cog.listener()
    async def on_guild_remove(self):
        """Log guild joins."""
        await update_server_count(self.home_guild, len(self.bot.guilds))

    @commands.Cog.listener()
    async def on_command_error(self, ctx, e):
        """Command Error Handler."""
        if self.owner:
            await self.owner.send(f"{vars(ctx)}\n{type(e)}\n{e}")

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
        message = SEARCH_RESULTS_FOUND.format(files.files[0].filename)[:100]
        await recipient.send(message, embed=embed, view=view)


async def setup(bot):
    """
    Set up the bot.

    Args:
        bot: The discord bot.
    """
    print(f'In {DB_NAME} mode')
    searcher = DiscordSearcher()
    command_client = FileDataClient(db_name=DB_NAME)
    await bot.add_cog(Haystackfs(guild_ids, bot, searcher, command_client))
