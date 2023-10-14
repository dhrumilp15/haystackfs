from discord.ext import commands
from python.discord_utils import update_server_count
from python.bot_secrets import GUILD_ID


class AdminCog(commands.Cog):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.home_guild = None
        self.owner = None

    @commands.Cog.listener()
    async def on_ready(self):
        appinfo = await self.bot.application_info()
        self.owner = appinfo.owner
        self.home_guild = self.bot.get_guild(GUILD_ID)

    @commands.Cog.listener()
    async def on_guild_join(self):
        """Log guild joins."""
        await update_server_count(self.home_guild, len(self.bot.guilds))

    @commands.Cog.listener()
    async def on_guild_remove(self):
        """Log guild joins."""
        await update_server_count(self.home_guild, len(self.bot.guilds))

    @commands.Cog.listener()
    async def on_command_error(self, ctx, e):
        """Command Error Handler."""
        if self.home_guild:
            await self.home_guild.send(f"{vars(ctx)}\n{type(e)}\n{e}")


def setup(bot):
    return AdminCog(bot)
