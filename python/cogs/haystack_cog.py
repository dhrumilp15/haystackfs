"""Cog class."""
import io
import json
import re
import hashlib

from python.models.query import Query
from python.bot_secrets import DB_NAME
import discord
from discord import app_commands
from discord.ext import commands
from python.utils import search_opts, CONTENT_TYPE_CHOICES
from python.bot_commands import fsearch
from python.export_template import generate_script
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

    def __init__(self, bot, search_client):
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
                interaction,
                send_source,
                edit_source,
                query.dm,
                search_results,
                query=query
            )
            if query.dm:
                await interaction.followup.send(content="Sent to your DMs!", ephemeral=True)

    @app_commands.command(name="export", description=EXPORT_COMMAND_DESCRIPTION)
    @app_commands.describe(**search_opts)
    @app_commands.choices(filetype=CONTENT_TYPE_CHOICES)
    @give_signature
    async def slash_export(self, interaction: discord.Interaction, query: Query):
        """Responds to `/export`. Builds a download script for all files matching a query."""
        send_source, edit_source = await self._get_send_and_edit_recipients(interaction=interaction, send=query.dm)
        search_results = await self.locate(interaction=interaction, query=query)
        if not search_results.files:
            await interaction.followup.send(content=search_results.message, ephemeral=query.dm)
            return

        # So file names are maximally compatible.
        def sanitize(s, default): return re.sub(r"[^A-Za-z0-9'\-\_ ]", "", s).rstrip() or default

        # Restrict to channels that the search returns files for. This is so that the
        # script does not leak the full server channel list every export. This mapping
        # is required so the export script can save files in directories named by the channels.
        needed_ids = set(str(f.channel_id) for f in search_results.files)
        if interaction.guild is None:
            chan = interaction.channel
            chan_name = getattr(chan, "name", None) or str(chan.id)
            channels = {str(chan.id): sanitize(chan_name, str(chan.id))}
            guild_name = sanitize(chan_name, "export")
        else:
            channels = {
                str(c.id): sanitize(c.name, str(c.id))
                for c in interaction.guild.channels
                if str(c.id) in needed_ids
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
                content=f"Found {len(search_results.files)} file{'s' if len(search_results.files) != 1 else ''}. Run this script to download them.",
                attachments=[discord.File(export_script, filename=filename)]
            )
        if query.dm:
            await interaction.followup.send(content="Sent to your DMs!", ephemeral=True)

    @app_commands.command(name="delete", description="Delete files AND their respective messages")
    @app_commands.describe(**search_opts)
    @app_commands.choices(filetype=CONTENT_TYPE_CHOICES)
    @give_signature
    async def slash_delete(self, interaction: discord.Interaction, query: Query):
        """Respond to `/delete`. Remove docs matching a query and their respective discord messages."""
        search_results = await self.locate(interaction=interaction, query=query)
        if not search_results.files:
            await interaction.followup.send(content=search_results.message, ephemeral=query.dm)
            return
        deleted_files = []
        for file in search_results.files:
            try:
                onii_chan = self.bot.get_channel(int(file.channel_id))
                if onii_chan is None:
                    continue
                message = await onii_chan.fetch_message(file.message_id)
                await message.delete()
                deleted_files.append(file.filename)
            except (discord.Forbidden, discord.errors.NotFound):
                continue
        if not deleted_files:
            await interaction.followup.send(content="No files were deleted.", ephemeral=True)
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
        if send:
            send_source = await interaction.user.create_dm()
        else:
            edit_source = await interaction.followup.send(content=SEARCHING_MESSAGE)
        return send_source, edit_source

    async def send_files_as_message(
        self,
        interaction: discord.Interaction,
        send_source,
        edit_source,
        send: bool,
        search_results: SearchResults,
        query: Query,
    ):
        """Send paginated `/search` results and persist their pagination state.

        Steps:
            1. Stash the cursor and serialize the query/initial page.
            2. INSERT a row in the pagination store to reserve a row_id.
            3. Build the FileView with that row_id baked into custom_ids.
            4. Send the message.
            5. Attach the message_id to the row and register the view persistently.
        """
        name = self.bot.user.name
        avatar_url = self.bot.user.display_avatar.url

        # 1. Serialize state.
        query.channel_date_map = search_results.channel_date_map
        query_json = query.to_json()
        pages_json = json.dumps({"1": search_results.to_dict()})

        # 2. Reserve a row_id BEFORE building the view so custom_ids are stable.
        row_id = await self.bot.pagination_store.create(
            user_id=interaction.user.id,
            channel_id=interaction.channel_id,
            guild_id=interaction.guild.id if interaction.guild else None,
            query_json=query_json,
            pages_json=pages_json,
        )

        # 3. Build view with row_id.
        view = FileView(search_results, row_id=row_id)
        embed = FileEmbed(search_results, name=name, avatar_url=avatar_url)
        body = interaction.user.mention + SEARCH_RESULTS_FOUND.format(
            search_results.files[0].filename
        )[:100]

        # 4. Send.
        sent_message = await send_or_edit(
            send_source=send_source,
            edit_source=edit_source,
            send=send,
            content=body,
            embed=embed,
            view=view,
        )

        # 5. Attach message_id and register the view persistently. If something
        #    goes wrong here, the row exists with message_id IS NULL and the
        #    vacuum task will sweep it.
        if sent_message is not None and getattr(sent_message, "id", None) is not None:
            await self.bot.pagination_store.attach_message(row_id, sent_message.id)
            self.bot.add_view(view, message_id=sent_message.id)


def setup(bot, search_client):
    """
    Set up the bot.

    Args:
        bot: The discord bot.
        search_client: Shared DiscordSearcher constructed in bot.py.
    """
    print(f'In {DB_NAME} mode')
    return Haystackfs(bot, search_client)
