import discord
from discord.ext.commands import Bot
import re
from python.bot_secrets import METRICS_CHANNEL_MAP
from python.bot_secrets import DB_NAME
from python.messages import ERROR_LOG_MESSAGE
import traceback


async def increment_command_count(bot: Bot, command_type: str, value: int = None):
    match_string = r'(?P<desc>[a-zA-Z_ ]*): ?(?P<count>[0-9]*)?'
    channel_id = METRICS_CHANNEL_MAP[DB_NAME][command_type]
    channel = bot.get_channel(channel_id)
    channel_name = channel.name
    match = re.search(match_string, channel_name)
    desc, count = match.groups()
    if value is None:
        value = int(count) + 1
    await channel.edit(name=f"{desc}: {value}")


async def send_or_edit(send_source, edit_source, send: bool, *args, **kwargs):
    if send:
        await send_source.send(*args, **kwargs)
    else:
        await edit_source.edit(*args, **kwargs)


async def post_exception(channel: discord.TextChannel, exc_tb, exc_val, command_type, query):
    tb_info = traceback.format_tb(exc_tb)
    await channel.send(ERROR_LOG_MESSAGE.format(command_type, query, ''.join(tb_info), str(exc_val)))
