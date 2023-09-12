import discord
from ..utils import search_opts
from .haystack_embed import HaystackEmbed


class HelpEmbed(HaystackEmbed):

    def __init__(self, name: str, avatar_url: str):
        """
        Build help embed.

        Returns:
            The help embed
        """
        super().__init__(title=f'{name}', name=name, avatar_url=avatar_url)
        super().add_field(name=f"What does {name} do?", value=f"Use {name} to search for your discord files.\n"
                                                              "Use commands to search, delete or remove files.\n"
                                                              "Specifying search options can refine your queries.")
        super().add_field(name="Search",
                          value="Use `/search` to search for files. Selecting no options retrieves all files.",
                          inline=False)
        super().add_field(name="Delete", value="Use `/delete` to specify files to delete", inline=False)
        super().add_field(name="Search Options", value="Use these to refine your search queries!", inline=False)
        for opt in search_opts:
            super().add_field(name=opt, value=search_opts[opt])
