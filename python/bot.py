"""Main Bot Controller."""
from config import CONFIG
import logging
from discord.ext import commands
import discord
from discord_slash import SlashCommand

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
# bot = discord.Client(intents=discord.Intents.default())
slash = SlashCommand(bot)

bot.load_extension('cog')

# @bot.command(name="reload")
# async def reload(ctx):
#     """Reload cog."""
#     # Reloads the file, thus updating the Cog class.
#     bot.reload_extension("cog")

bot.run(TOKEN)
