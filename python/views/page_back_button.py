import discord

from .pagination_callbacks import handle_back_click


class PageBackButton(discord.ui.Button):
    def __init__(self, *, row_id: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Previous Page",
            custom_id=f"hfs:back:{row_id}",
        )
        self.row_id = row_id

    async def callback(self, interaction: discord.Interaction):
        await handle_back_click(interaction, self.row_id)
