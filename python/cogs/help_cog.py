from discord.ext import commands
from discord import app_commands
import discord
from python.views.help_view import HelpEmbed


class HelpCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="A help command")
    @app_commands.describe(dm="If true, I'll dm results to you.")
    async def slash_help(self, interaction: discord.Interaction, dm: bool = False) -> None:
        """Respond to /help. Display a help command with commands and search options."""
        await interaction.response.defer(ephemeral=dm)
        name = self.bot.user.name
        avatar_url = self.bot.user.display_avatar.url
        await interaction.followup.send(embed=HelpEmbed(name=name, avatar_url=avatar_url), ephemeral=dm)


def setup(bot):
    return HelpCog(bot)
