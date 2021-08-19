"""Main Bot Controller."""
from config import CONFIG
import logging
from discord.ext import commands
import discord
from discord_slash import SlashCommand
from datetime import datetime

dlogger = logging.getLogger('discord')
dlogger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
handler.setFormatter(formatter)
dlogger.addHandler(handler)


TOKEN = CONFIG.DISCORD_TOKEN
if getattr(CONFIG, 'DB_NAME', None) == "testing":
    TOKEN = getattr(CONFIG, 'TEST_DISCORD_TOKEN', CONFIG.DISCORD_TOKEN)
bot = commands.Bot(command_prefix='fs!', intents=discord.Intents.all())
slash = SlashCommand(bot, sync_commands=True)

bot.load_extension('cog')


@slash.slash(
    name="reload",
    description="Reloads the cog file. Use this to deploy changes to the bot",
    guild_ids=[int(getattr(CONFIG, "GUILD_ID", 0))]
)
async def reload(ctx):
    """Reload cog if the bot owner requests a reload."""
    appinfo = await bot.application_info()
    if ctx.author == appinfo.owner:
        print(f"Reload initiated by {appinfo.owner} at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}!")
        await ctx.send('Reloading!')
        # Reloads the file, updating the Cog class.
        bot.reload_extension("cog")


@bot.command()
async def reload(ctx):
    """Reload the bot."""
    appinfo = await bot.application_info()
    if ctx.author == appinfo.owner:
        print(f"Reload initiated by {appinfo.owner} at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}!")
        # Reloads the file, updating the Cog class.
        bot.reload_extension("cog")

bot.run(TOKEN)
