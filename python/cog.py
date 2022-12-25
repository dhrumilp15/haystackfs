"""Cog class."""
from cryptography.fernet import Fernet
from functools import reduce, wraps
from security.SymmetricMessageEncryptor import SymmetricMessageEncryptor
from search.async_search_client import AsyncSearchClient
from search.past_file_search import PastFileSearch
from mongo_client import MgClient
from config import CONFIG
import logging
from discord import app_commands
from utils import search_options, dm_option
from bot_commands import fdelete, fremove, fsearch
from export_template import generate_script
from discord.ext import commands, tasks
import discord
import datetime
from dateutil import parser
import glob
from typing import List, Dict, Tuple, Union, Optional
import io
import re
import hashlib

guild_ids = []
if getattr(CONFIG, "GUILD_ID", None):
    guild_ids = [discord.Object(id=int(CONFIG.GUILD_ID))]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
fh = logging.FileHandler('main.log', encoding='utf-8', mode='w')
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


class Discordfs(commands.Cog):
    """Main class for the bot."""

    def __init__(self, guild_ids: list, bot,
                 search_client: AsyncSearchClient,
                 db_client: MgClient,
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

        ok = self.initialize_clients(self.bot)

        if self.guild_ids:
            self.bot.tree.add_command(self.slash_help, guild=guild_ids[0])
            await self.bot.tree.sync(guild=guild_ids[0])
            print("Synced slash help!!")
        if ok:
            print("Clients Initialized!")

    def initialize_clients(self, *args, **kwargs) -> bool:
        """Initialize search and db clients."""
        return self.search_client.initialize(*args, **kwargs)

    def log_command(function):
        """
        Log commands from the given function.

        To be used with search, delete and remove functions.
        """
        @wraps(function)
        async def wrapper(self, *args, **kwargs):
            await self.db_client.log_command(function, *args, **kwargs)
            return await function(self, *args, **kwargs)
        return wrapper


    def interface_function(function):
        """
        Default wrapper for most public interface functions
        """
        @wraps(function)
        @app_commands.Argument(**search_options[0])
        @app_commands.Argument(**search_options[1])
        @app_commands.Argument(**search_options[2])
        @app_commands.Argument(**search_options[3])
        @app_commands.Argument(**search_options[4])
        @app_commands.Argument(**search_options[5])
        @app_commands.Argument(**search_options[6])
        @app_commands.Argument(**search_options[7])
        async def wrapper(self, *args, **kwargs):
            return await function(self, *args, **kwargs)
        return wrapper

    def build_help_embed(self) -> discord.Embed:
        """
        Build help embed.

        Returns:
            The help embed
        """
        name = self.bot.user.name
        avatar_url = self.bot.user.display_avatar.url
        embed = discord.Embed(title=f'{name}', color=discord.Color.teal())
        embed.add_field(name=f"What does {name} do?",
                        value=f"Use {name} to search for your discord files.\n"
                        "Use commands to search, delete or remove files.\n"
                        "Specifying search options can refine your queries.")
        embed.add_field(name="Search",
                        value="Use `/search` to search for files. Selecting no options retrieves all files.",
                        inline=False)
        embed.add_field(name="Delete", value="Use `/delete` to specify files to delete", inline=False)
        embed.add_field(name="Remove", value="Use `/remove` to specify files to make unsearchable", inline=False)
        embed.add_field(name="Search Options", value="Use these to refine your search queries!", inline=False)
        for search_opt in search_options:
            embed.add_field(name=search_opt['name'],
                            value=search_opt['description'])
        embed.set_footer(text=f"Delivered by {name}, a better file manager for discord.",
                         icon_url=avatar_url)
        return embed

    @app_commands.command(
        name="help",
        description="A help command",
        # options=[dm_option],
        # guild_ids=guild_ids if getattr(CONFIG, "DB_NAME", "production") == "testing" else []
    )
    @app_commands.describe(dm="If true, I'll dm results to you.")
    async def slash_help(self, interaction: discord.Interaction, dm: Optional[bool]=False) -> None:
        """
        Responds to /help. Displays a help command with commands and search options.

        Args:
            interaction: The context from which the command was issued
            dm: Whether to display the command only to the author
        """
        await interaction.response.defer(ephemeral=dm)
        embed = self.build_help_embed()
        await interaction.followup.send(embed=embed, ephemeral=dm)

    async def locate(self, ctx: discord.Interaction, **kwargs
    ) -> Tuple[Union[discord.Interaction, discord.member.Member, discord.user.ClientUser], List[Dict]]:
        """
        Turn arguments into a search and return the files.

        Args:
            ctx: The SlashContext from which the command originated
            filename: A str of the filename to query for.
            DM: A bool for whether to dm the author the results.

        Returns a destination that has a .send method, and a list of files.
        """
        await ctx.defer(hidden=kwargs.get("dm", False))
        try:
            await self.db_client.log_command(**kwargs)
        except:
            pass

        if kwargs.get("before"):
            before = parser.parse(kwargs.get("before"))
            # Long way to do it but I'm not sure how else to do this
            before = datetime.datetime(*before.timetuple()[:3])
            before += datetime.timedelta(days=1) - datetime.timedelta(microseconds=1)
            kwargs['before'] = before
        if kwargs.get("after"):
            after = parser.parse(kwargs.get("after"))
            after = datetime.datetime(*after.timetuple()[:3])
            after -= datetime.timedelta(microseconds=1)
            kwargs['after'] = after

        if kwargs.get("channel") and ctx.guild is not None:
            if not kwargs.get("channel").permissions_for(ctx.guild.me).read_message_history:
                await ctx.send(f"I can't read messages in {kwargs.get('channel').name}! Please give me `read_message_history` permissions for {kwargs.get('channel').name}", hidden=kwargs.get("dm", False))
                return ctx, []
        files = await fsearch(ctx=ctx, search_client=self.search_client, bot=self.bot, **kwargs)
        # TODO: Better Error Handling
        if isinstance(files, str):
            await ctx.send(content=files, hidden=True)
            return ctx, []

        recipient = ctx
        if kwargs.get("dm"):
            recipient = ctx.author
            await ctx.send("DM'ing your files...", hidden=True)

        return recipient, files

    @app_commands.command(
        name="search",
        description="Search for files.",
        # options=search_options,
        # guild_ids=guild_ids if getattr(CONFIG, "DB_NAME", "production") == "testing" else []
    )
    @interface_function
    async def slash_search(self, ctx: discord.Interaction, filename: Optional[str]=None):
        """
        Responds to `/search`. Tries to display docs related to a query from ElasticSearch.

        Args:
            ctx: The SlashContext from which the command originated
            filename: A str of the filename to query for.
            DM: A bool for whether to dm the author the results.
        """
        recipient, files = await self.locate(ctx)
        if files:
            await self.send_files_as_message(recipient, files)

    @app_commands.command(
        name="export",
        description="Get a Python export script to download the files returned in a search to your computer.",
        # options=search_options,
        # guild_ids=guild_ids if getattr(CONFIG, "DB_NAME", "production") == "testing" else []
    )
    @interface_function
    async def slash_export(self, ctx: discord.Interaction, **kwargs):
        """
        Responds to `/export`. Tries get a download script for all files related to a query from ElasticSearch.

        Args:
            ctx: The SlashContext from which the command originated.
            filename: A str of the filename to query for, if any.
            DM: A bool for whether to dm the author the results.
        """
        recipient, files = await self.locate(ctx, **kwargs)
        if not files:
            return

        # So file names are maximally compatible.
        def sanitize(s, default): return re.sub(r"[^A-Za-z0-9'\-\_ ]", "", s).rstrip() or default

        # Restrict to channels that the search returns files for. This is so that the
        # script does not leak the full server channel list every export. This mapping
        # is required so the export script can save files in directories named by the channels.
        needed_ids = set(f["channel_id"] for f in files)
        if ctx.guild is None:
            chan = ctx.channel
            channels = {str(chan.id): sanitize(chan, str(chan.id))}
            guild_name = sanitize(chan.name, "export")
        else:
            channels = {
                str(c.id): sanitize(c.name, str(c.id))
                for c in ctx.guild.channels
                if c.id in needed_ids
            }
            guild_name = sanitize(ctx.guild.name, "export")

        # This is so that if one is running multiple exports in a server,
        # they don't get export(1).py etc.
        unique_suffix = hashlib.sha256(bytes(str(sorted(f["url"] for f in files)), "utf-8")).hexdigest()[:5]
        filename = f"export_{guild_name}_{unique_suffix}.py"
        with io.StringIO(generate_script(guild_name, files, channels)) as export_script:
            await recipient.send(
                f"Found {len(files)} file(s). Run this script to download them.",
                file=discord.File(export_script, filename=filename)
            )

    @app_commands.command(
        name="delete",
        description="Delete files AND their respective messages",
        # options=search_options,
        # guild_ids=guild_ids if getattr(CONFIG, "DB_NAME", "production") == "testing" else []
    )
    @log_command
    @interface_function
    async def slash_delete(self, ctx: discord.Interaction, **kwargs):
        """
        Responds to `/delete`. Tries to remove docs related to a query and their respective discord messages.

        Args:
            ctx: The SlashContext from which the command originated
            filename: A str of the filename to query for.
        """
        await ctx.defer(hidden=True)
        deleted_files = await fdelete(ctx, self.search_client, self.db_client, self.bot, **kwargs)
        if isinstance(deleted_files, str):
            await ctx.send(content=deleted_files, hidden=True)
            return
        await ctx.send(content=f"Deleted {' '.join(deleted_files)}", hidden=True)

    @app_commands.command(
        name="remove",
        description="Remove files from index (These files will no longer be searchable!!)",
        # options=search_options,
        # guild_ids=guild_ids if getattr(CONFIG, "DB_NAME", "production") == "testing" else []
    )
    @log_command
    @interface_function
    async def slash_remove(self, ctx: discord.Interaction, **kwargs):
        """
        Responds to `/remove`. Tries to remove docs related to a query from applicable search indices.

        Args:
            ctx: The SlashContext from which the command originated
            filename: A str of the filename to query for.
        """
        await ctx.defer(hidden=True)
        removed_files = await fremove(ctx, self.search_client, self.db_client, self.bot, **kwargs)
        if isinstance(removed_files, str):
            await ctx.send(content=removed_files, hidden=True)
            return
        await ctx.send(content=f"Removed {' '.join(removed_files)}", hidden=True)

    @commands.command(name="fsearch", aliases=["fs", "search", "s"], pass_context=True)
    @log_command
    async def classic_search(self, ctx: commands.Context, filename: str):
        """
        Find and send files related to a query.

        Args:
            ctx: The commands.Context from which the command originated
            filename: A str of the filename to query for.
        """
        files = await fsearch(ctx, filename, self.search_client, self.bot)
        if isinstance(files, str):
            await ctx.author.send(content=files)
            return
        await self.send_files_as_message(ctx, files)

    @commands.command(name="delete", aliases=["del"], pass_context=True)
    @log_command
    async def classic_delete(self, ctx: commands.Context, filename: str):
        """
        Delete docs related to the given filename from ElasticSearch and their respective messages.

        Args:
            ctx: The commands.Context from which the command originated
            filename: A str of the filename to query for
        """
        files = await fdelete(ctx, self.search_client, self.db_client, self.bot, filename=filename)
        if isinstance(files, str):
            await ctx.author.send(files)
            return
        await ctx.author.send("Deleted: " + ' '.join(files))

    @commands.command(name="remove", aliases=["rm"], pass_context=True)
    @log_command
    async def classic_remove(self, ctx, filename):
        """
        Remove docs related to the given filename from ElasticSearch.

        Args:
            ctx: The commands.Context from which the command originated
            filename: A str of the filename to query for
        """
        files = await fremove(ctx, self.search_client, self.db_client, self.bot, filename=filename)
        if isinstance(files, str):
            await ctx.author.send(files)
            return
        await ctx.author.send("Removed: " + ' '.join(files))

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

    @commands.Cog.listener()
    async def on_component(self, ctx):
        """
        Update origin component.

        Edits the embed of the existing message.
        """
        if ctx.component_type == 3:
            embed = ctx.origin_message.embeds[0]
            name = ""
            payload = ctx.selected_options[0]
            for opt in ctx.component['options']:
                if opt['value'] == payload:
                    name = opt['label']
                    break
            channel_id, message_id, file_id = payload.split(',')
            if ctx.guild is not None:
                jump_url = f"https://discord.com/channels/{ctx.guild.id}/{channel_id}/{message_id}"
                media_url = f"https://cdn.discordapp.com/attachments/{channel_id}/{file_id}/{name}"
            embed.set_field_at(index=0, name=name, value=jump_url)
            embed.set_image(url=media_url)
            await ctx.edit_origin(embed=embed)

    async def send_files_as_message(self, ctx: discord.Interaction, files: List[Dict]):
        """
        Send files as a message to ctx.

        Args:
            ctx: The originating context.
            files: The files to send to the context.
        """
        print(files)
        print("SEND MESSAGE!!")
        # files = files[:25]
        # if len(files) <= 5:
        #     buttons = [create_button(style=ButtonStyle.URL,
        #                              label=f['filename'],
        #                              url=f['jump_url']) for f in files]
        #     action_row = create_actionrow(*buttons)
        # else:
        #     options = []
        #     for file in files:
        #         name = file['filename']
        #         if len(name) >= 100:
        #             name = name[:97] + '...'
        #         option = create_select_option(
        #             label=name,
        #             value=','.join(map(str, [file['channel_id'], file['message_id'], file['objectID']]))
        #         )
        #         options.append(option)
        #     select = create_select(
        #         options=options,
        #         placeholder="Choose your files here!",
        #         min_values=1,
        #         max_values=1
        #     )
        #     action_row = create_actionrow(select)
        # embed = discord.Embed(
        #     title=f"Found {len(files)} file{'s' if len(files) > 1 else ''}",
        #     color=discord.Colour.teal())
        # embed.set_footer(
        #     text=f"Delivered by {self.bot.user.name}, a better file manager for discord.",
        #     icon_url=self.bot.user.avatar_url)
        # filename = files[0].get('filename')
        # mediaUrl = files[0].get('jump_url')
        # if not mediaUrl:
        #     file_id = files[0]['objectID']
        #     res = await self.db_client.get_file(file_id)
        #     mediaUrl = res['url']
        # embed.insert_field_at(index=0, name=filename, value=mediaUrl, inline=False)
        # if files[0].get('content_type', None):
        #     if 'image' in files[0]['content_type']:
        #         embed.set_image(url=files[0]['url'])
        # await ctx.send(f"Found {files[0]['filename']} {'and more...' if len(files) > 1 else ''}",
        #                embed=embed, components=[action_row])


async def setup(bot):
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
    sme = SymmetricMessageEncryptor(Fernet, CONFIG)
    await bot.add_cog(Discordfs(guild_ids, bot, searcher, mg_client, sme))
