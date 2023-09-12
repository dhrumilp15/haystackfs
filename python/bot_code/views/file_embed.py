import discord
from .file_view import FileView
from ..search.search_models import SearchResults


class FileEmbed(discord.Embed):

    def __init__(self, files: SearchResults, name: str, avatar_url: str):
        """
        Build file search embed.

        Returns:
            The help embed
        """
        first_file = files.files[0]
        super().__init__(
            title=f"Found {len(files.files)} file{'s' if len(files.files) > 1 else ''}",
            color=discord.Colour.teal()
        )
        super().set_footer(text=f"Delivered by {name}, a better file manager for discord.",
                           icon_url=avatar_url)
        filename = first_file.filename[:100]
        mediaUrl = first_file.jump_url

        super().insert_field_at(index=0, name=filename, value=mediaUrl, inline=False)
        if first_file.content_type:
            if 'image' in first_file.content_type:
                super().set_image(url=first_file.url)
