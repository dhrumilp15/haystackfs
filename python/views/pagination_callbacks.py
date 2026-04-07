"""Persistent pagination callback logic.

`PageNextButton` / `PageBackButton` callbacks delegate here. This module owns
the read-modify-write against `PaginationStore` and the message re-render.

State lives entirely in the store; the View instances are stateless wrappers
holding only `row_id`. That makes the callbacks safe to invoke after a bot
restart that rehydrated the view via `bot.add_view(view, message_id=...)`.
"""
import json
from datetime import datetime

import discord

from ..bot_commands import fsearch
from ..models.query import Query
from ..search.search_models import SearchResults


async def _guard(interaction: discord.Interaction, store, row_id: str):
    """Common preflight: load row, check ownership, defer the interaction.

    Returns the row dict on success, or None if the caller should bail.
    """
    row = await store.load(row_id)
    if row is None:
        await interaction.response.send_message(
            "This search has expired. Run `/search` again.", ephemeral=True
        )
        return None
    if interaction.user.id != row["user_id"]:
        await interaction.response.send_message(
            "Only the user who ran the search can paginate it.", ephemeral=True
        )
        return None
    await interaction.response.defer()
    return row


async def handle_next_click(interaction: discord.Interaction, row_id: str) -> None:
    store = interaction.client.pagination_store
    searcher = interaction.client.search_client
    async with await store.lock_for(row_id):
        row = await _guard(interaction, store, row_id)
        if row is None:
            return
        await _advance(interaction, store, searcher, row)


async def handle_back_click(interaction: discord.Interaction, row_id: str) -> None:
    store = interaction.client.pagination_store
    async with await store.lock_for(row_id):
        row = await _guard(interaction, store, row_id)
        if row is None:
            return
        await _retreat(interaction, store, row)


async def _advance(interaction, store, searcher, row) -> None:
    pages = json.loads(row["pages_json"])
    current = row["current_page"]
    last = row["last_page"]

    query_blob = row["query_json"]
    query = Query.from_json(query_blob, bot=interaction.client)

    # Stale-lookup detection: if the original query referenced a channel/author
    # the bot can no longer see, give up rather than silently filtering against
    # a None object.
    raw = json.loads(query_blob)
    if (raw.get("author_id") and query.author is None) or \
       (raw.get("channel_id") and query.channel is None):
        await store.delete(row["row_id"])
        await interaction.followup.send(
            "This search references a channel or user the bot can no longer see. "
            "Run `/search` again.", ephemeral=True,
        )
        return

    if current != last:
        current += 1

    if str(current) not in pages and current != last:
        in_prog = _build_in_progress_embed(interaction.message, current)
        await interaction.message.edit(embed=in_prog, view=None)

        sr = await fsearch(interaction, searcher, query)
        if not sr.files:
            current -= 1
            last = current
        else:
            pages[str(current)] = sr.to_dict()
            if sr.channel_date_map:
                query.channel_date_map = sr.channel_date_map
            else:
                last = current

    await store.update(
        row["row_id"],
        pages_json=json.dumps(pages),
        current_page=current,
        last_page=last,
        query_json=query.to_json(),
    )
    await _rerender(interaction, row["row_id"], pages, current, last)


async def _retreat(interaction, store, row) -> None:
    pages = json.loads(row["pages_json"])
    current = row["current_page"]
    last = row["last_page"]

    if current <= 1:
        # Already at the first page; nothing to do beyond a quiet ack.
        return

    current -= 1
    await store.update(
        row["row_id"],
        pages_json=json.dumps(pages),
        current_page=current,
        last_page=last,
        query_json=row["query_json"],
    )
    await _rerender(interaction, row["row_id"], pages, current, last)


async def _rerender(interaction, row_id: str, pages: dict, current: int, last: int) -> None:
    """Edit the message with a fresh embed + view for the current page."""
    from .file_view import FileView, build_page_embed  # lazy to avoid circular import

    page_results = SearchResults.from_dict(pages[str(current)])
    embed = build_page_embed(interaction.message, page_results, current)
    view = FileView(page_results, row_id=row_id)
    await interaction.message.edit(embed=embed, view=view)


def _build_in_progress_embed(message: discord.Message, current_page: int) -> discord.Embed:
    embed = message.embeds[0]
    embed.clear_fields()
    embed.set_image(url=None)
    embed.title = f"Gathering files for page {current_page}..."
    footer_text = embed.footer.text or ""
    idx = footer_text.find("Delivered")
    footer_text = footer_text[idx:] if idx != -1 else footer_text
    embed.set_footer(text=footer_text, icon_url=embed.footer.icon_url)
    return embed
