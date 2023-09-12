from .haystack_embed import HaystackEmbed
from ..search.search_models import SearchResults


class FileEmbed(HaystackEmbed):

    def __init__(self, search_results: SearchResults, name: str, avatar_url: str):
        """
        Build file search embed.

        Returns:
            The help embed
        """
        super().__init__(
            title=f"Found {len(search_results.files)} file{'s' if len(search_results.files) > 1 else ''}",
            name=name, avatar_url=avatar_url
        )
        first_file = search_results.files[0]
        filename = first_file.filename[:100]
        mediaUrl = first_file.jump_url

        super().insert_field_at(index=0, name=filename, value=mediaUrl, inline=False)
        if first_file.content_type:
            if 'image' in first_file.content_type:
                super().set_image(url=first_file.url)
