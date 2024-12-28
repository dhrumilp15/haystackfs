import discord


class PageBackButton(discord.ui.Button):
    def __init__(self, fileview: 'FileView'):
        super().__init__(style=discord.ButtonStyle.secondary, label="Previous page")
        self.fileview = fileview

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.fileview.previous_page(interaction)
