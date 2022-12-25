"""Main Bot Controller."""
from config import CONFIG
import logging
from discord.ext import commands
from discord import app_commands
import discord
from datetime import datetime
import asyncio
from typing import Literal, Optional
from discord.ext import commands
from discord.ext.commands import Greedy, Context # or a subclass of yours

# logging
dlogger = logging.getLogger('discord')
dlogger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
handler.setFormatter(formatter)
dlogger.addHandler(handler)

# bot init
TOKEN = CONFIG.DISCORD_TOKEN
if getattr(CONFIG, 'DB_NAME', None) == "testing":
    TOKEN = getattr(CONFIG, 'TEST_DISCORD_TOKEN', CONFIG.DISCORD_TOKEN)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='fs!', intents=intents)
# slash = SlashCommand(bot, sync_commands=True)


debug_guild = [discord.Object(id=int(CONFIG.GUILD_ID))] if getattr(CONFIG, "GUILD_ID", None) else []

@bot.tree.command(
    name="reload",
    description="Reloads the cog file. Use this to deploy changes to the bot",
    guilds=debug_guild
)
@commands.is_owner()
async def reload(interaction: discord.Interaction):
    """Reload cog if the bot owner requests a reload."""
    appinfo = await bot.application_info()
    print(f"Reload initiated by {appinfo.owner} at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}!")
    await interaction.response.send_message('Reloading!')
    # Reloads the file, updating the Cog class.
    await bot.reload_extension("cog")


@bot.command()
@commands.is_owner()
@commands.guild_only()
async def reload(ctx: Context):
    """Reload the bot."""
    appinfo = await bot.application_info()
    print(f"{bot.user} Reload initiated by {appinfo.owner} at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}!")
    # Reloads the file, updating the Cog class.
    await bot.reload_extension("cog")

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

        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
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

if __name__ == "__main__":
    async def main():
        # Sync commands after loading extensions
        async with bot:
            await bot.load_extension('cog')
            await bot.start(TOKEN)
    asyncio.run(main())
