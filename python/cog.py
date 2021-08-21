"""Cog class."""
from search.async_search_client import AsyncSearchClient
from search.past_file_search import PastFileSearch
from search.searcher import Searcher
from search.algolia_client import AlgoliaClient
from mongo_client import MgClient
from utils import attachment_to_search_dict, search_options
from bot_commands import fdelete, fremove, fsearch
from config import CONFIG
import logging
from discord_slash import SlashContext, cog_ext
from discord_slash.utils.manage_components import create_select, create_select_option, create_actionrow, create_button
from discord_slash.model import ButtonStyle
from discord_slash.context import ComponentContext
from discord.ext import commands, tasks, menus
import discord
import datetime
from dateutil import parser
import glob
from typing import List, Dict
from MultiPageEmbed import MultiPageEmbed

guild_ids = []
if getattr(CONFIG, "GUILD_ID", None):
    guild_ids = [int(CONFIG.GUILD_ID)]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
fh = logging.FileHandler('main.log', encoding='utf-8', mode='w')
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


class Discordfs(commands.Cog):
    """Main class for the bot."""

    def __init__(self, guild_ids: list, bot, search_client: AsyncSearchClient, db_client: MgClient):
        """Instantiate the bot."""
        self.bot = bot
        self.guild_ids = guild_ids
        self.owner = None
        self.search_client = search_client
        self.db_client = db_client
        self.initialize_clients(self.bot.user)

    @commands.Cog.listener()
    async def on_ready(self):
        """Occurs when the discord client is ready."""
        appinfo = await self.bot.application_info()
        self.owner = appinfo.owner
        print(f'{self.bot.user} has connected to Discord!')
        print(f'{self.owner} is my owner!')
        print(f'Guild ids: {self.guild_ids}')
        ok = self.initialize_clients(self.bot.user)
        if ok:
            print("Clients Initialized!")

    def initialize_clients(self, *args, **kwargs) -> bool:
        """Initialize search and db clients."""
        return self.search_client.initialize(*args, **kwargs)

    @cog_ext.cog_slash(
        name="search",
        description="Search for files.",
        options=search_options,
        guild_ids=guild_ids if getattr(CONFIG, "DB_NAME", "production") == "testing" else []
    )
    async def _search(self, ctx: SlashContext, filename: str, filetype: str = None, custom_filetype: str = None,
                      author: discord.User = None, channel: discord.channel = None, content: str = None, after: str = None,
                      before: str = None, dm: bool = False):
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
        files = await fsearch(ctx=ctx, filename=filename, search_client=self.search_client, bot=self.bot, mimetype=filetype,
                              author=author, content=content, channel=channel, after=after, before=before)
        if isinstance(files, str):
            await ctx.send(content=files, hidden=True)
            return
        author = ctx
        if dm:
            author = ctx.author
        await self.send_files_as_message(author, files, self.db_client)

    @cog_ext.cog_slash(
        name="delete",
        description="Delete files AND their respective messages",
        options=search_options,
        guild_ids=guild_ids if getattr(CONFIG, "DB_NAME", "production") == "testing" else []
    )
    async def _delete(self, ctx, filename, **kwargs):
        """
        Responds to `/delete`. Tries to remove docs related to a query from ElasticSearch and their respective discord messages.

        Args:
            ctx: The SlashContext from which the command originated
            filename: A str of the filename to query for.
        """
        await ctx.defer()
        deleted_files = await fdelete(ctx, filename, self.search_client, self.db_client, self.bot, **kwargs)
        if isinstance(deleted_files, str):
            await ctx.send(content=deleted_files, hidden=True)
            return
        await ctx.send(content=f"Deleted {' '.join(deleted_files)}", hidden=True)

    @cog_ext.cog_slash(
        name="remove",
        description="Remove files from index (These files will no longer be searchable!!)",
        options=search_options,
        guild_ids=guild_ids if getattr(CONFIG, "DB_NAME", "production") == "testing" else []
    )
    async def _remove(self, ctx: SlashContext, filename: str, **kwargs):
        """
        Responds to `/remove`. Tries to remove docs related to a query from ElasticSearch.

        Args:
            ctx: The SlashContext from which the command originated
            filename: A str of the filename to query for.
        """
        await ctx.defer()
        removed_files = await fremove(ctx, filename, self.search_client, self.db_client, self.bot, **kwargs)
        if isinstance(removed_files, str):
            await ctx.send(content=removed_files, hidden=True)
            return
        await ctx.send(content=f"Removed {' '.join(removed_files)}", hidden=True)

    @commands.command(name="fsearch", aliases=["fs", "search", "s"], pass_context=True)
    async def search(self, ctx: commands.Context, filename: str):
        """
        Display docs related to a query from ElasticSearch.

        Args:
            ctx: The commands.Context from which the command originated
            filename: A str of the filename to query for.
        """
        files = await fsearch(ctx, filename, self.search_client, self.bot)
        if isinstance(files, str):
            await ctx.author.send(content=files)
            return
        await self.send_files_as_message(ctx, files, self.db_client)

    @commands.command(name="delete", aliases=["del"], pass_context=True)
    async def delete(self, ctx: commands.Context, filename: str):
        """
        Delete docs related to the given filename from ElasticSearch and their respective messages.

        Args:
            ctx: The commands.Context from which the command originated
            filename: A str of the filename to query for
        """
        deleted_files = await fdelete(ctx, filename, self.search_client, self.db_client, self.bot)
        if isinstance(deleted_files, str):
            await ctx.author.send(deleted_files)
            return
        await ctx.author.send("Deleted: " + ' '.join(deleted_files))

    @commands.command(name="remove", aliases=["rm"], pass_context=True)
    async def remove(self, ctx, filename):
        """
        Remove docs related to the given filename from ElasticSearch.

        Args:
            ctx: The commands.Context from which the command originated
            filename: A str of the filename to query for
        """
        removed_files = await fremove(ctx, filename, self.search_client, self.db_client, self.bot)
        if isinstance(removed_files, str):
            await ctx.author.send(removed_files)
            return
        await ctx.author.send("Removed: " + ' '.join(removed_files))

    @commands.Cog.listener()
    async def on_slash_command(self, ctx: SlashContext):
        """Attempt to create an index for a channel on each command."""
        serv = ctx.channel
        if ctx.guild is not None:
            serv = ctx.guild
        await self.db_client.add_server(serv)

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
        serv = message.channel
        if message.guild is not None:
            serv = message.guild
        await self.db_client.add_server(serv)
        for file in message.attachments:
            meta_dict = attachment_to_search_dict(message, file)
            await self.search_client.create_doc(meta_dict, serv.id, message.author.name + "#" + message.author.discriminator)
            saved_files = await self.db_client.add_file(message)
            # if saved_files:
            # await message.channel.send(f"Saved {len(message.attachments)}
            # file{'s' if len(message.attachments) > 1 else ''}")

        await self.bot.process_commands(message)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        """
        Handle message deletion. Removes the respective documents from the index.

        This is also called when we delete messages in `_delete()`, but that's not
        a problem since we only remove docs from indices if they exist.

        Args:
            payload: A discord.RawMessageDeleteEvent event.
        """
        if payload.cached_message is None:
            onii_chan_id = payload.channel_id
            chan = await self.bot.fetch_channel(onii_chan_id)
        else:
            message = payload.cached_message
            # if the message is cached, we'll know whether the author is a bot user
            if message.author == self.bot.user:
                return
            chan = message.channel
            onii_chan_id = message.channel
            if message.guild is not None:
                onii_chan_id = message.guild
        files = await self.search_client.search(payload.message_id, onii_chan_id, chan)
        await self.search_client.remove_doc([file['objectID'] for file in files], onii_chan_id, "bot_deletion")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """
        Log guild joins.

        Args:
            guild: The discord.Guild that the bot just joined
        """
        await self.db_client.add_server(guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """
        Log guild joins.

        Args:
            guild: The discord.Guild that the bot just joined
        """
        await self.db_client.remove_server(guild.id)
        await self.db_client.remove_server_docs(guild.id)
        await self.search_client.clear(guild.id)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, e):
        """Command Error Handler."""
        if self.owner:
            await self.owner.send(f"{type(e)}\n{e}")

    @tasks.loop(hours=24)
    async def clear_irrelevant_docs(self):
        """Run a simple cleaner every 24 hours."""
        ack, ok = await self.db_client.delete_files_from_inactive_servers()
        if not ok:
            logger.error("Deleted every element in the collection, restoring the database now...")
            snaps = sorted(glob.glob(f"{getattr(CONFIG, 'DB_NAME', 'normal')}_files/*"), reverse=True)[0]
            await self.db_client.load_from_snapshot(snaps)
            logger.debug("Database restored!")

    @commands.Cog.listener()
    async def on_component(self, ctx: ComponentContext):
        """
        Update origin component.

        Edits the embed of the existing message.
        """
        embed = ctx.origin_message.embeds[0]
        name = ""
        jump_url = ctx.selected_options[0]
        for opt in ctx.component['options']:
            if opt['value'] == jump_url:
                name = opt['label']
                break
        embed.set_field_at(index=0, name=name, value=jump_url)
        await ctx.edit_origin(embed=embed)

    async def cog_command_error(ctx, error):
        """Command error."""
        print(error)

    async def send_files_as_message(self, ctx: SlashContext, files: List[Dict], mg_client: MgClient):
        """
        Send files as a message to ctx.

        Args:
            ctx: The originating context.
            files: The files to send to the context.
            mg_client: The Mongodb client. Used only when 'jump_url' doesn't exist.
        """
        if len(files) <= 5:
            buttons = [create_button(style=ButtonStyle.URL, label=f['file_name'], url=f['jump_url']) for f in files]
            action_row = create_actionrow(*buttons)
        else:
            select = create_select(
                options=[create_select_option(file['file_name'], value=file['jump_url']) for file in files],
                placeholder="Choose your files here!",
                min_values=1,
                max_values=1,
            )
            action_row = create_actionrow(select)
        embed = discord.Embed(
            title=f"Found {len(files)} files",
            color=discord.Colour.teal(),
        )
        embed.set_footer(
            text=f"Delivered by {self.bot.user.name}, a better file manager for discord.",
            icon_url=self.bot.user.avatar_url
        )
        filename = files[0].get('file_name')
        mediaUrl = files[0].get('jump_url')
        if not mediaUrl:
            file_id = files[0]['objectID']
            res = await mg_client.get_file(file_id)
            mediaUrl = res['url']
        embed.insert_field_at(index=0, name=filename, value=mediaUrl, inline=False)
        await ctx.send(f"Found {len(files)} files", embed=embed, components=[action_row])


def setup(bot):
    """
    Set up the bot.

    Args:
        bot: The discord bot.
    """
    print(f'In {getattr(CONFIG, "DB_NAME", "normal")} mode')
    # ag_client = AlgoliaClient(getattr(CONFIG, 'ALGOLIA_APP_ID', None), getattr(CONFIG, 'ALGOLIA_SEARCH_KEY', None),
    #                           getattr(CONFIG, 'ALGOLIA_ADMIN_KEY', None))
    # searcher = Searcher(ag_client, PastFileSearch())
    searcher = PastFileSearch()
    mg_client = MgClient(getattr(CONFIG, 'MONGO_ENDPOINT', None), getattr(CONFIG, 'DB_NAME', None))
    bot.add_cog(Discordfs(guild_ids, bot, searcher, mg_client))
