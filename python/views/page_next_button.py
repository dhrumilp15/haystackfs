import discord

class PageNextButton(discord.ui.Button):
    def __init__(self, fileview: 'FileView'):
        super().__init__(style=discord.ButtonStyle.secondary, label="Next Page")
        self.fileview = fileview

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.fileview.next_page(interaction)


