"""Cog class."""
from python.search.discord_searcher import DiscordSearcher
from python.models.query import Query
from python.bot_secrets import DB_NAME
import discord
from discord import app_commands
from discord.ext import commands
from python.utils import search_opts, CONTENT_TYPE_CHOICES
from python.bot_commands import fdelete, fsearch
from python.export_template import generate_script
import io
import re
import hashlib
from python.views.file_view import FileView
from python.views.file_embed import FileEmbed
from python.search.search_models import SearchResults
from python.messages import (
    INSUFFICIENT_BOT_PERMISSIONS,
    EXPORT_COMMAND_DESCRIPTION,
    SEARCH_RESULTS_FOUND,
    SEARCHING_MESSAGE,
)
from python.discord_utils import send_or_edit
from python.cogs.utils import give_signature


class Haystackfs(commands.Cog):
    """Main class for the bot."""

    def __init__(self,
                 bot,
                 search_client):
        """Instantiate the bot."""
        self.bot = bot
        self.owner = None
        self.search_client = search_client

    @commands.Cog.listener()
    async def on_ready(self):
        """Occurs when the discord client is ready."""
        appinfo = await self.bot.application_info()
        self.owner = appinfo.owner
        print(f'{self.bot.user} has connected to Discord!')
        print(f'{self.owner} is my owner!')
        # await update_server_count(self.home_guild, len(self.bot.guilds))
        # print("updated server count")

    async def locate(self, interaction: discord.Interaction, query: Query) -> SearchResults:
        """
        Turn arguments into a search and return the files.

        Args:
            interaction: The SlashContext from which the command originated
            query: The user query

        Returns a destination that has a .send method, and a list of files.
        """
        if query.channel and interaction.guild is not None:
            if not query.channel.permissions_for(interaction.guild.me).read_message_history:
                return SearchResults(
                    message=INSUFFICIENT_BOT_PERMISSIONS.format(query.channel.name, query.channel.name)
                )
        return await fsearch(interaction=interaction, search_client=self.search_client, query=query)

    @app_commands.command(name="search", description="Search for your files!")
    @app_commands.describe(**search_opts)
    @app_commands.choices(filetype=CONTENT_TYPE_CHOICES)
    @give_signature
    async def slash_search(self, interaction: discord.Interaction, query: Query):
        """Responds to `/search`. Tries to display docs that match a query."""
        send_source, edit_source = await self._get_send_and_edit_recipients(interaction=interaction, send=query.dm)
        search_results = await self.locate(interaction=interaction, query=query)
        if not search_results.files:
            await interaction.followup.send(content=search_results.message, ephemeral=query.dm)
        else:
            await self.send_files_as_message(
                interaction.user.mention,
                send_source,
                edit_source,
                query.dm,
                search_results
            )

    @app_commands.command(name="export", description=EXPORT_COMMAND_DESCRIPTION)
    @app_commands.describe(**search_opts)
    @app_commands.choices(filetype=CONTENT_TYPE_CHOICES)
    @give_signature
    async def slash_export(self, interaction: discord.Interaction, query: Query):
        """Responds to `/export`. Builds a download script for all files matching a query."""
        send_source, edit_source = await self._get_send_and_edit_recipients(interaction=interaction, send=query.dm)
        search_results = await self.locate(interaction=interaction, query=query)
        if search_results.message:
            await interaction.followup.send(content=search_results.message, ephemeral=query.dm)
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
            await send_or_edit(
                send_source=send_source,
                edit_source=edit_source,
                send=query.dm,
                content=f"Found {len(search_results.files)} file(s). Run this script to download them.",
                file=discord.File(export_script, filename=filename)
            )

    @app_commands.command(name="delete", description="Delete files AND their respective messages")
    @app_commands.describe(**search_opts)
    @app_commands.choices(filetype=CONTENT_TYPE_CHOICES)
    @give_signature
    async def slash_delete(self, interaction: discord.Interaction, query: Query):
        """Respond to `/delete`. Remove docs matching a query and their respective discord messages."""
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

    @staticmethod
    async def _get_send_and_edit_recipients(interaction, send):
        send_source = interaction.followup
        edit_source = None
        if not send:
            edit_source = await interaction.followup.send(content=SEARCHING_MESSAGE)
        return send_source, edit_source

    async def send_files_as_message(self, mention: str, send_source, edit_source, send: bool, search_results: SearchResults):
        """
        Send files as a message to ctx.

        Args:
            ctx: The originating context.
            search_results: The files to send to the context.
        """
        name = self.bot.user.name
        avatar_url = self.bot.user.display_avatar.url
        if len(search_results.files) > 25:
            search_results.files = search_results.files[:25]
        view = FileView(search_results)
        embed = FileEmbed(search_results, name=name, avatar_url=avatar_url)
        message = SEARCH_RESULTS_FOUND.format(search_results.files[0].filename)[:100]
        await send_or_edit(
            send_source=send_source,
            edit_source=edit_source,
            send=send,
            content=mention + message,
            embed=embed,
            view=view
        )


def setup(bot):
    """
    Set up the bot.

    Args:
        bot: The discord bot.
    """
    print(f'In {DB_NAME} mode')
    searcher = DiscordSearcher()
    return Haystackfs(bot, searcher)
