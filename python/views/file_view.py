"""Persistent paginated view for `/search` results.

`FileView` is a thin component carrier — it owns no pagination state. State
lives in `PaginationStore`, keyed by the `row_id` baked into each component's
`custom_id`. The view is registered with `bot.add_view(view, message_id=...)`
so clicks survive bot restarts.
"""
import discord

from .file_dropdown import FileDropDown
from .file_button import FileButton
from .page_back_button import PageBackButton
from .page_next_button import PageNextButton
from ..search.search_models import SearchResult, SearchResults


class FileView(discord.ui.View):
    def __init__(
        self,
        results: SearchResults,
        *,
        row_id: str,
        current_page: int = 1,
        last_page: int = 1,
    ):
        """Persistent view for one page of search results.

        Pagination buttons are included only when needed:
            - Back button only when current_page > 1.
            - Next button only when current_page != last_page (more pages exist
              or are unknown — last_page == -1 is the "more pages" sentinel).
            - Neither when current_page == 1 == last_page (single-page result).

        `bot.add_view(view, message_id=...)` is called on every edit, so the
        registered component shape always matches what's currently on the message.
        """
        super().__init__(timeout=None)
        self.row_id = row_id

        files = results.files or []
        if 0 < len(files) <= 5:
            for file in files:
                self.add_item(FileButton(file))
        else:
            self.add_item(FileDropDown(results, row_id=row_id))

        if current_page > 1:
            self.add_item(PageBackButton(row_id=row_id))
        if current_page != last_page:
            self.add_item(PageNextButton(row_id=row_id))


def build_page_embed(
    message: discord.Message, results: SearchResults, current_page: int
) -> discord.Embed:
    """Mutate the embed currently on `message` to preview the first file of `results`."""
    embed = message.embeds[0]
    preview_file: SearchResult = results.files[0]

    guild_segment = str(message.guild.id) if message.guild is not None else "@me"
    jump_url = (
        f"https://discord.com/channels/{guild_segment}/"
        f"{preview_file.channel_id}/{preview_file.message_id}"
    )
    media_url = (
        f"https://cdn.discordapp.com/attachments/"
        f"{preview_file.channel_id}/{preview_file.objectId}/{preview_file.filename}"
    )

    num_files = len(results.files)
    embed.title = f"Found {num_files} file{'s' if num_files != 1 else ''}"
    embed.clear_fields()
    embed.insert_field_at(index=0, name=preview_file.filename[:256], value=jump_url)
    embed.set_image(url=media_url)

    footer_text = embed.footer.text or ""
    idx = footer_text.find("Delivered")
    if idx != -1:
        footer_text = footer_text[idx:]
    embed.set_footer(text=f"Page {current_page}, {footer_text}", icon_url=embed.footer.icon_url)
    return embed
