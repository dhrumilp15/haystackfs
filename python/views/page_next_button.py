import discord

from .pagination_callbacks import handle_next_click


class PageNextButton(discord.ui.Button):
    def __init__(self, *, row_id: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Next Page",
            custom_id=f"hfs:next:{row_id}",
        )
        self.row_id = row_id

    async def callback(self, interaction: discord.Interaction):
        await handle_next_click(interaction, self.row_id)
