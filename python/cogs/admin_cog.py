from discord.ext import commands
from python.discord_utils import update_server_count
from python.bot_secrets import GUILD_ID


class AdminCog(commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.home_guild = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.home_guild = self.bot.get_guild(GUILD_ID)
        await update_server_count(self.home_guild, len(self.bot.guilds))

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Log guild joins."""
        await update_server_count(self.home_guild, len(self.bot.guilds))

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """Log guild joins."""
        await update_server_count(self.home_guild, len(self.bot.guilds))


def setup(bot):
    return AdminCog(bot)
