import discord
from ..search.search_models import SearchResult


class FileButton(discord.ui.Button):
    def __init__(self, file: SearchResult):
        super().__init__(style=discord.ButtonStyle.url, label=file.filename[:80], url=file.jump_url)
