"""Search for files purely in discord."""
from .async_search_client import AsyncSearchClient
import discord
from typing import List, Union
from ..models.query import Query
import asyncio
from fuzzywuzzy import fuzz
from .search_models import SearchResults, SearchResult
from time import time


class DiscordSearcher(AsyncSearchClient):
    """Search for files in discord with just discord."""

    def __init__(self, thresh: int = 75):
        """
        Create a DiscordSearch object.

        Args:
            thresh: The string similarity threshold to determine a match
        """
        self.banned_file_ids = set()
        self.thresh = thresh
        self.search_result_limit = 25

    async def chan_search(self, onii_chan: discord.TextChannel, query: Query, files, file_set, channel_date_map) -> List[SearchResult]:
        """
        Search a channel index for a query.

        Args:
            onii_chan: The channel to search
            query: The query to use to search the channel

        Yields:
            A list of dicts of files
        """

        messages = onii_chan.history(limit=None, before=query.before, after=query.after)
        async for message in messages:
            if len(files) >= self.search_result_limit:
                channel_date_map[onii_chan.id] = message.created_at
                break
            if not message.attachments:
                continue
            metadatas = list(map(lambda atch: SearchResult.from_discord_attachment(message, atch), message.attachments))
            for metadata in metadatas:
                if metadata.objectId in self.banned_file_ids or metadata.objectId in file_set:
                    continue
                if metadata.match_query(query=query, thresh=self.thresh):
                    if metadata.objectId not in file_set:
                        file_set.add(metadata.objectId)
                        files.append(metadata)

    async def search(self, interaction: discord.Interaction, onii_chans: List[Union[discord.DMChannel, discord.Guild]],
                     bot_user=None, query: Query = None) -> SearchResults:
        """
        Search all channels in a Guild or the provided channel.

        Args:
            ctx: The original context for response
            onii_chans: A list of channels to search
            bot_user: The name of the bot
            query: Search parameters

        Returns:
            A list of dicts of files.
        """
        onii_chans = list(filter(lambda chan: chan.permissions_for(bot_user).read_message_history, onii_chans))
        files = []
        files_set = set()
        tasks = []
        # getting files from each channel one at a time is really slow, but
        channel_date_map = {chan.id: None for chan in onii_chans}

        for onii_chan in onii_chans:
            tasks.append(self.chan_search(onii_chan, query, files, files_set, channel_date_map))
        await asyncio.gather(*tasks)
        if query.filename:
            files = sorted(files, reverse=True, key=lambda x: fuzz.ratio(query.filename, x.filename))
        elif query.content:
            files = sorted(files, reverse=True, key=lambda x: fuzz.ratio(query.content, x.content))
        return SearchResults(files=files, channel_date_map=channel_date_map)

    async def create_doc(self, *args, **kwargs):
        """We don't store any docs in this searcher, so it doesn't matter"""
        pass

    async def remove_doc(self, file_ids: list, *args, **kwargs):
        """Update banned ids with the file ids."""
        pass
