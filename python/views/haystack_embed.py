import discord


class HaystackEmbed(discord.Embed):

    def __init__(self, title: str, name: str, avatar_url: str):
        super().__init__(title=title, color=discord.Colour.teal())
        super().set_footer(text=f"Delivered by {name}, a file search engine for discord.", icon_url=avatar_url)
