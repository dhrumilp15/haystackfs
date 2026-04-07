"""Main Bot Controller."""
import json
import os
from python.bot_secrets import DISCORD_TOKEN, TEST_DISCORD_TOKEN, DB_NAME, GUILD_ID
import logging
import discord
from datetime import datetime
import asyncio
from typing import Literal, Optional
from discord.ext import commands
from discord.ext.commands import Greedy, Context
from python.messages import RELOAD_DESCRIPTION
from python.cogs.haystack_cog import setup as haystack_setup
from python.cogs.admin_cog import setup as admin_setup
from python.cogs.help_cog import setup as help_setup
from python.persistence.pagination_store import PaginationStore
from python.search.discord_searcher import DiscordSearcher
from python.search.search_models import SearchResults
from python.views.file_view import FileView


DB_PATH = os.environ.get(
    "HAYSTACK_DB_PATH",
    "/var/lib/haystackfs/pagination.sqlite3",
)
TTL_SECONDS = 24 * 3600
VACUUM_INTERVAL_SECONDS = 3600


# logging
dlogger = logging.getLogger('discord')
dlogger.setLevel(logging.ERROR)
handler = logging.FileHandler(filename='logs/discord.log', encoding='utf-8', mode='w')
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
handler.setFormatter(formatter)
dlogger.addHandler(handler)

# bot init
TOKEN = DISCORD_TOKEN
if DB_NAME == "testing" or DB_NAME is None:
    TOKEN = TEST_DISCORD_TOKEN
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='fs!', intents=intents)
debug_guild = [] if not GUILD_ID else [discord.Object(id=GUILD_ID)]


@bot.tree.command(name="reload", description=RELOAD_DESCRIPTION, guilds=debug_guild)
@commands.is_owner()
async def reload(interaction: discord.Interaction):
    """Reload cog if the bot owner requests a reload."""
    appinfo = await bot.application_info()
    print(f"Reload initiated by {appinfo.owner} at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}!")
    await interaction.response.send_message('Reloading!')
    # Reloads the file, updating the Cog class.
    await bot.reload_extension("cog")


# umbra's sync command. TYSM!!! <3
@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(ctx: Context, guilds: Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}")
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


async def _vacuum_loop(store: PaginationStore):
    while True:
        try:
            n = await store.vacuum_old(TTL_SECONDS)
            if n:
                print(f"[pagination] vacuumed {n} rows")
        except Exception as e:
            print(f"[pagination] vacuum failed: {e!r}")
        await asyncio.sleep(VACUUM_INTERVAL_SECONDS)


async def _rehydrate_views(bot: commands.Bot, store: PaginationStore):
    """Re-register persistent FileViews for every active row at startup."""
    rows = await store.iter_active(TTL_SECONDS)
    rehydrated = 0
    for row in rows:
        try:
            pages = json.loads(row["pages_json"])
            current_results = SearchResults.from_dict(pages[str(row["current_page"])])
            view = FileView(
                current_results,
                row_id=row["row_id"],
                current_page=row["current_page"],
                last_page=row["last_page"],
            )
            bot.add_view(view, message_id=row["message_id"])
            rehydrated += 1
        except Exception as e:
            print(f"[pagination] failed to rehydrate row {row['row_id']}: {e!r}")
    print(f"[pagination] rehydrated {rehydrated} views")


if __name__ == "__main__":
    async def main():
        async with bot:
            # 1. Construct shared services BEFORE adding cogs.
            bot.search_client = DiscordSearcher()
            bot.pagination_store = PaginationStore(DB_PATH)
            await bot.pagination_store.init()

            # 2. Add cogs (haystack cog now takes the shared search_client).
            await bot.add_cog(haystack_setup(bot, bot.search_client))
            await bot.add_cog(admin_setup(bot))
            await bot.add_cog(help_setup(bot))

            # 3. Rehydrate persistent views from the store.
            await _rehydrate_views(bot, bot.pagination_store)

            # 4. Background vacuum.
            bot._vacuum_task = asyncio.create_task(_vacuum_loop(bot.pagination_store))

            await bot.start(TOKEN)
    asyncio.run(main())
