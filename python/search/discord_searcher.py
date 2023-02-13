"""Search for files purely in discord."""
from .async_search_client import AsyncSearchClient
import discord
from typing import List, Dict, Union
from utils import attachment_to_mongo_dict, attachment_to_search_dict
from search.search_utils import search_dict_match
import asyncio
from fuzzywuzzy import fuzz
import datetime


class DiscordSearcher(AsyncSearchClient):
    """Search for files in discord with just discord."""

    def __init__(self, thresh: int = 75):
        """
        Create a DiscordSearch object.

        It's annoying to need bot_user but we do this to enable searching on files from other bots.

        Args:
            bot_user: The name of the bot user.
        """
        self.banned_file_ids = set()
        self.thresh = thresh
        self.user = None

    def initialize(self, bot_user: str, *args, **query) -> bool:
        """
        Initialize past file search.

        Args:
            bot_user: The bot username.
        """
        self.user = bot_user
        return True

    async def channel_index(self, channel: discord.TextChannel, before: datetime.datetime = None,
                            after: datetime.datetime = None) -> discord.Message:
        """
        Index a channel's files.

        Args:
            channel: The channel to index

        Yields:
            A list of dicts of file metadata
        """
        messages = channel.history(limit=None, before=before, after=after)
        count = 0
        async for message in messages:
            if count == 100:
                break
            if message.attachments:
                count += 1
                yield map(lambda atchmt: attachment_to_search_dict(message, atchmt), message.attachments)


    async def chan_search(self, onii_chan: discord.TextChannel, **query) -> List[Dict]:
        """
        Search a channel index for a query.

        Args:
            onii_chan: The channel to search
            query: The query to use to search the channel

        Yields:
            A list of dicts of files
        """
        if self.user is None:
            return []

        files = []
        files_set = set()
        async for message in self.channel_index(onii_chan, before=query["before"], after=query["after"]):
            for metadata in message:
                if metadata['objectID'] in self.banned_file_ids or metadata['objectID'] in files_set:
                    continue
                if search_dict_match(metadata=metadata, thresh=self.thresh, **query):
                    files.append(metadata)
                    files_set.add(metadata['objectID'])
        return files, files_set

    async def search(self, interaction: discord.Interaction, onii_chans: List[Union[discord.DMChannel, discord.Guild]],
                     bot_user=None, **query) -> List[Dict]:
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
        if self.user is None:
            return []

        if query.get('banned_ids'):
            query['banned_ids'].update(self.banned_file_ids)
        else:
            query['banned_ids'] = self.banned_file_ids

        onii_chans = list(filter(lambda chan: chan.permissions_for(bot_user).read_message_history, onii_chans))
        tasks = []
        for onii_chan in onii_chans:
            tasks.append(asyncio.ensure_future(self.chan_search(onii_chan, **query)))
        res = await asyncio.gather(*tasks)
        files = []
        big_set = set()
        for file_list, file_set in res:
            files.extend(file_list)
            big_set.union(file_set)
        files = list(filter(lambda file: file['objectID'] not in big_set, files))
        if query.get('filename'):
            return sorted(files, reverse=True, key=lambda x: fuzz.ratio(query['filename'], x['filename']))
        elif query.get('content'):
            return sorted(files, reverse=True, key=lambda x: fuzz.ratio(query['content'], x['content']))
        return files

    async def create_doc(self, *args, **kwargs):
        """We don't store any docs in this searcher, so it doesn't matter"""
        pass

    async def remove_doc(self, file_ids: list, *args, **kwargs):
        """Update banned ids with the file ids."""
        pass
