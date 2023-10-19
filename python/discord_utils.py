import discord
from discord.ext.commands import Bot
import re
from python.bot_secrets import METRICS_CHANNEL_MAP
from python.bot_secrets import DB_NAME
from python.bot_secrets import ERROR_CHANNEL_ID
from python.bot_secrets import GUILD_ID
from python.messages import ERROR_LOG_MESSAGE, ERROR_SUPPORT_MESSAGE
import traceback


async def update_server_count(home_guild: discord.Guild, num_guilds: int):
    if home_guild is None:
        return
    name = f"Server Count: {num_guilds}"
    category_name = "BOT STATS"
    category = None
    for cat in home_guild.categories:
        if cat.name == category_name:
            category = cat
            break
    if category is None:
        category = await home_guild.create_category_channel(name=category_name)
        await home_guild.create_voice_channel(name=name, category=category, user_limit=0)
    else:
        channels = category.voice_channels
        edited = False
        for chan in channels:
            if chan.name.startswith("Server Count: "):
                try:
                    await chan.edit(name=name)
                    edited = True
                except:
                    pass
        if not edited:
            try:
                await home_guild.create_voice_channel(name=name, category=category, user_limit=0)
            except:
                pass


async def increment_command_count(bot: Bot, command_type: str):
    match_string = r'(?P<desc>[a-zA-Z_]*: )(?P<count>[0-9]*)'
    channel_id = METRICS_CHANNEL_MAP[DB_NAME][command_type]
    channel = bot.get_channel(channel_id)
    channel_name = channel.name
    match = re.search(match_string, channel_name)
    desc = match.group('desc')
    count = int(match.group('count')) + 1
    await channel.edit(name=f"{desc}{count}")


async def post_exception(command_type: str, query, source, args, tb, bot):
    print("Command error!!")
    home_guild = bot.get_guild(GUILD_ID)
    channel = home_guild.get_channel(ERROR_CHANNEL_ID)
    tb_info = traceback.format_tb(tb)
    await channel.send(ERROR_LOG_MESSAGE.format(command_type, query, ''.join([''.join(tb_info), "\n", str(args)])))
    await source.send(ERROR_SUPPORT_MESSAGE)


async def send_or_edit(send_source, edit_source, send: bool, *args, **kwargs):
    if send:
        await send_source.send(*args, **kwargs)
    else:
        await edit_source.edit(*args, **kwargs)