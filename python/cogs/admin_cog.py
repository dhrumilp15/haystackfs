from discord.ext import commands
from python.discord_utils import increment_command_count
from python.bot_secrets import GUILD_ID


class AdminCog(commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await increment_command_count(self.bot, "server_count", len(self.bot.guilds))

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Log guild joins."""
        await increment_command_count(self.bot, "server_count", len(self.bot.guilds))

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """Log guild joins."""
        await increment_command_count(self.bot, "server_count", len(self.bot.guilds))


def setup(bot):
    return AdminCog(bot)
