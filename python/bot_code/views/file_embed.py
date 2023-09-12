from .haystack_embed import HaystackEmbed
from ..search.search_models import SearchResults
from ..messages import SEARCH_RESULTS_FOUND


class FileEmbed(HaystackEmbed):

    def __init__(self, search_results: SearchResults, name: str, avatar_url: str):
        """Build file search embed."""
        super().__init__(
            title=SEARCH_RESULTS_FOUND.format(len(search_results.files)) + " file(s)",
            name=name, avatar_url=avatar_url
        )
        first_file = search_results.files[0]
        filename = first_file.filename[:100]
        mediaUrl = first_file.jump_url

        super().insert_field_at(index=0, name=filename, value=mediaUrl, inline=False)
        if first_file.is_image():
            super().set_image(url=first_file.url)
