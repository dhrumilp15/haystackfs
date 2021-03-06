"""Search for files purely in discord."""
from .async_search_client import AsyncSearchClient
import discord
from typing import List, Dict, Union, Tuple
from fuzzywuzzy import fuzz
from utils import attachment_to_mongo_dict, attachment_to_search_dict
import datetime
import json
import os
from pathlib import Path
from dateutil import parser
import datetime
import asyncio


class PastFileSearch(AsyncSearchClient):
    """Search for files in discord with just discord."""

    def __init__(self, thresh: int = 75, indices_fp: str = "indices"):
        """
        Create a DiscordSearch object.

        It's annoying to need bot_user but we do this to enable searching on files from other bots.

        Args:
            bot_user: The name of the bot user.
        """
        self.banned_file_ids = set()
        self.thresh = thresh
        self.user = None
        self.indices_fp = indices_fp
        Path(indices_fp).mkdir(exist_ok=True)

    def initialize(self, bot_user: str, *args, **query) -> bool:
        """
        Initialize past file search.

        Args:
            bot_user: The bot username.
        """
        self.user = bot_user
        return True
    
    async def channel_index(self, channel: discord.TextChannel) -> Tuple[int, List[Dict]]:
        """
        Index a channel's files.

        Args:
            channel: The channel to index

        Returns:
            A list of dicts of file metadata
        """
        messages = channel.history(limit=None)
        chan_messages = []
        async for message in messages:
            if message.attachments:
                chan_messages.extend([attachment_to_search_dict(message, f) for f in message.attachments])
        return (channel.id, chan_messages)
    
    def load_index(self, source_id: int) -> Union[Dict[int, List], bool]:
        if os.path.exists(f"{self.indices_fp}/{source_id}.json"):
            with open(f'{self.indices_fp}/{source_id}.json', 'r') as f:
                chan_map = json.load(f)
                return chan_map
        else:
            return False
    
    def save_index(self, chan_map: Dict[int, List], source_id: int):
        with open(f'{self.indices_fp}/{source_id}.json', 'w') as f:
            json.dump(chan_map, fp=f, indent=4)

    async def build_index(self, ctx, source: Union[discord.DMChannel, discord.Guild], channel: discord.TextChannel = None) -> Dict:
        """
        Build an index of files from a server/channel.

        Args:
            ctx: The DM Channel or Guild that is being searched
            channel: An optional channel to search through

        Returns:
            An index of files in a server or channel
        """
        if isinstance(source, discord.Guild):
            channels = source.text_channels
        else:
            channels = [source]
        chan_map = self.load_index(source.id)
        to_index = channels
        if not chan_map:
            await ctx.send("I haven't yet indexed the channel or server. I may take a while to respond depending on the number of messages in your channel.")
            chan_map = {}
        else:
            to_index = []
            for chan in channels:
                if str(chan.id) not in chan_map:
                    to_index.append(chan)
            if not to_index:
                if channel is None:
                    return chan_map
                if channel in chan_map:
                    return chan_map
        if channel is not None:
            chan_map[str(channel.id)], _ = await self.channel_index(channel)
        else:
            chan_list = [chan for chan in to_index if chan.permissions_for(source.me).read_message_history]
            indices = await asyncio.gather(*[self.channel_index(chan) for chan in chan_list])
            for channel_id, index in indices:
                chan_map[str(channel_id)] = index
        chan_map['last_indexed'] = datetime.datetime.now().isoformat()
        self.save_index(chan_map, source.id)
        return chan_map

    def search_dict_match(self, search_dict: Dict, **query: Dict) -> bool:
        """
        Match the query against a file's search dict.

        Args:
            search_dict: The file to match
            query: Query Arguments

        Returns:
            A list of discord.Attachments that match the query.
        """
        if query.get("content"):
            if fuzz.partial_ratio(query['content'].lower(), search_dict['content'].lower()) < self.thresh:
                return False
        created_at = parser.parse(search_dict['created_at'])
        if query.get("after"):
            if created_at < query["after"]:
                return False
        if query.get("before"):
            if created_at > query["before"]:
                return False
        if query.get("author"):
            if search_dict['author_id'] != query["author"].id:
                return False
        if query.get("channel"):
            if search_dict['channel_id'] != query["channel"].id:
                return False
        if query.get('filename'):
            if fuzz.partial_ratio(query['filename'].lower(),
                                  search_dict['filename'].lower()) < self.thresh:
                return False
        if query.get('custom_filetype'):
            if fuzz.partial_ratio(query['custom_filetype'].lower(),
                                  search_dict['filetype'].lower()) < self.thresh:
                return False
        if query.get("filetype"):
            filetype = search_dict['content_type']
            if filetype is None:
                filetype = search_dict['filetype']
            if query['filetype'] == 'image':
                if 'image' not in filetype:
                    return False
            elif query['filetype'] == 'audio':
                if 'audio' not in filetype:
                    return False
            else:
                if query['filetype'] != filetype:
                    return False
        if query.get("banned_ids"):
            if search_dict['objectID'] in query['banned_ids']:
                return False
        return True

    def chan_search(self, chan_index: Dict, **query) -> List[Dict]:
        """
        Search a channel index for a query.

        Args:
            chan_index: The index of the channel
            query: The query to use to search the channel

        Returns:
            A list of dicts of files
        """
        if self.user is None:
            return []
        return [file for file in chan_index if self.search_dict_match(file, **query)]

    async def search(
        self, ctx, onii_chan: Union[discord.DMChannel, discord.Guild], bot_user=None, *args, **query
    ) -> List[Dict]:
        """
        Search all channels in a Guild or the provided channel.

        Args:
            onii_chan: The channel/guild to search
            kawrgs: Search paramaters

        Returns:
            A list of dicts of files.
        """
        if self.user is None:
            return []

        if query.get('banned_ids'):
            query['banned_ids'].update(self.banned_file_ids)
        else:
            query['banned_ids'] = self.banned_file_ids

        chan_map = await self.build_index(ctx, onii_chan)
        files = []
        if isinstance(onii_chan, discord.DMChannel):
            files = await self.chan_search(chan_map[str(onii_chan.id)], *args, **query)
        elif isinstance(query.get("channel"), discord.TextChannel):
            if query['channel'].permissions_for(bot_user).read_message_history:
                files = await self.chan_search(chan_map[str(query['channel'].id)], *args, **query)
        else:
            for chan in onii_chan.text_channels:
                if chan.permissions_for(bot_user).read_message_history:
                    if str(chan.id) not in chan_map:
                        chan_map = await self.build_index(ctx, onii_chan)
                    chan_files = self.chan_search(chan_map[str(chan.id)], *args, **query)
                    files.extend(chan_files)
        if query.get('filename', None):
            return sorted(files, reverse=True, key=lambda x: fuzz.ratio(query['filename'], x['filename']))
        return files

    async def create_doc(self, file: discord.File, message: discord.Message, *args, **kwargs):
        """
        Update the search index for the corresponding server/channel with the new file.

        Args:
            file: The file to save
            message: The message in which the file is sent
        """
        if message.guild is not None:
            source = message.guild
        else:
            source = message.channel
        filename = os.path.join(self.indices_fp, f'{source.id}.json')
        # only maintain indices for servers that run commands
        if not os.path.exists(filename):
            return
        with open(filename, 'r') as f:
            chan_map = json.load(f)

        key = str(message.channel.id)
        if key in chan_map:
            chan_map[key].append(attachment_to_search_dict(message, file))
        else:
            chan_map[key] = [attachment_to_search_dict(message, file)]
        with open(filename, 'w') as f:
            json.dump(chan_map, fp=f, indent=4)

    async def clear(self, *args, **kwargs):
        """We don't maintain search indices in this class, so this is not needed."""
        return

    async def remove_doc(self, file_ids: list, *args, **kwargs):
        """Update banned ids with the file ids."""
        for file_id in file_ids:
            self.banned_file_ids.add(file_id)
