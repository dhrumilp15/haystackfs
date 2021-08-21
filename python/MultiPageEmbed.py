"""MultiPage Embed Class."""
from discord.ext import menus

# Originally authored by @EricIzEpic


class MultiPageEmbed(menus.ListPageSource):
    """MuliPage Embed Class."""

    async def format_page(self, menu, entry):
        """Format the page here."""
        return entry
