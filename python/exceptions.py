from .messages import ERROR_SUPPORT_MESSAGE
from .messages import ERROR_LOG_MESSAGE
import traceback
from python.bot_secrets import ERROR_CHANNEL_ID
from python.bot_secrets import GUILD_ID


class QueryException(Exception):
    def __init__(self, message):
        self.message = message


class GeneralExceptionHandler:

    def __init__(self, interaction, bot, command_type: str):
        self.interaction = interaction
        self.bot = bot
        self.query = None
        home_guild = self.bot.get_guild(GUILD_ID)
        self.channel = home_guild.get_channel(ERROR_CHANNEL_ID)
        self.command_type = command_type

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is QueryException:
            await self.interaction.followup.send(exc_val.message)
        elif exc_type is not None:
            await self.interaction.followup.send(content=ERROR_SUPPORT_MESSAGE, ephemeral=True)
            tb_info = traceback.format_tb(exc_tb)
            await self.channel.send(ERROR_LOG_MESSAGE.format(self.command_type, self.query, ''.join(tb_info), str(exc_val)))
