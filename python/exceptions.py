from .messages import ERROR_SUPPORT_MESSAGE
from python.bot_secrets import ERROR_CHANNEL_ID
from python.bot_secrets import GUILD_ID
from python.discord_utils import post_exception
from python.discord_utils import increment_command_count


class QueryException(Exception):
    def __init__(self, message):
        self.message = message


class CommandHandler:

    def __init__(self, interaction, bot, command_type: str, query):
        self.interaction = interaction
        self.bot = bot
        self.query = query
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
            await post_exception(self.channel, exc_tb, exc_val, self.command_type, self.query)
        await increment_command_count(self.bot, self.command_type)
