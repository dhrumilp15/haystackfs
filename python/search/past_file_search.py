"""Search for files purely in discord."""
from .async_search_client import AsyncSearchClient
import discord
from typing import List, Dict, Union, Tuple
from fuzzywuzzy import fuzz
from utils import attachment_to_mongo_dict, attachment_to_search_dict
import json
from pathlib import Path
from dateutil import parser
import asyncio
import os
import itertools
import heapq


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
        self.write_buffer_size = 50
        Path(indices_fp).mkdir(exist_ok=True)

    def initialize(self, bot_user: str, *args, **query) -> bool:
        """
        Initialize past file search.

        Args:
            bot_user: The bot username.
        """
        self.user = bot_user
        return True
    
    async def channel_index(self, channel: discord.TextChannel) -> discord.Message:
        """
        Index a channel's files.

        Args:
            channel: The channel to index

        Yields:
            A list of dicts of file metadata
        """
        messages = channel.history(limit=None)
        async for message in messages:
            if message.attachments:
                yield map(attachment_to_search_dict, message.attachments)

    def construct_index_file_path(self, onii_chan: discord.TextChannel) -> str:
        """
        Builds the filepath to an index for a discord channel.

        Args:
            onii_chan: The origin text channel

        Returns:
            A filepath string that's "{self.indices_fp}/{guild id}/{channel id}.json" for a guild channel or
            "{self.indices_fp}/{channel id}.json"
        """
        source = onii_chan.id
        filepath = str(source.id)
        if onii_chan.guild is not None:
            filepath = os.path.join(str(onii_chan.guild.id), filepath)
        filepath += ".json"
        return filepath

    async def load_index(self, ctx, onii_chans: List[Union[discord.DMChannel, discord.TextChannel]]):
        """
        Builds indices for the target channels if needed

        Args:
            ctx: The original interaction that created the search request
            onii_chans: The source text channels
        """
        responded = False
        for onii_chan in onii_chans:
            filepath = self.construct_index_file_path(onii_chan)
            if not os.path.exists(filepath):
                if not responded:
                    await ctx.send("I haven't indexed this channel/server and may take a while to respond.")
                    responded = True
                buffer = {}
                async for file_attachments in self.channel_index(onii_chan):

                    while file_attachments:
                        existing_files = buffer.get(filepath, [])
                        remaining_length = self.write_buffer_size - len(existing_files)
                        new_achmts = list(itertools.islice(file_attachments, remaining_length))
                        buffer[filepath] = existing_files.extend(new_achmts)
                        if len(buffer[filepath]) > self.write_buffer_size:
                            self.create_doc(filepath_to_metadata=buffer)
                            buffer[filepath] = []
                if buffer:
                    self.create_doc(filepath_to_metadata=buffer)

    def chan_search(self, onii_chan: discord.TextChannel, **query) -> List[Dict]:
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
        filepath = self.construct_index_file_path(onii_chan=onii_chan)
        files = []
        with open(filepath, 'r') as f:
            for md in f.readlines():
                metadata = json.loads(md)
                for key, value in query.items():
                    if key == "content" or key == "filename" or key == "custom_filetype":
                        score = fuzz.partial_ratio(value.lower(), metadata[key].lower())
                        if score < self.thresh:
                            break
                    elif key == "after":
                        if metadata['created_at'] < value:
                            break
                    elif key == "before":
                        if metadata['created_at'] > value:
                            break
                    elif key == "author" or key == "channel":
                        if metadata[key + "_id"] != value:
                            break
                    elif key == "filetype":
                        filetype = metadata['content_type']
                        if filetype is None:
                            filetype = metadata['filetype']
                        if value == 'image' or value == 'audio':
                            if value not in filetype:
                                break
                        else:
                            if value != filetype:
                                break
                else:
                    if metadata['objectID'] not in self.banned_file_ids:
                        files.append(metadata)

    async def search(self, ctx, onii_chans: List[Union[discord.DMChannel, discord.Guild]], bot_user=None, **query) -> List[Dict]:
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

        onii_chans = list(filter(lambda chan: chan.permissions_for(self.user).read_message_history, onii_chans))
        await self.load_index(ctx, onii_chans)
        files = []

        for onii_chan in onii_chans:
            matched_files = self.chan_search(onii_chan, **query)
            files.extend(matched_files)

        if query.get('filename'):
            return sorted(files, reverse=True, key=lambda x: fuzz.ratio(query['filename'], x['filename']))
        elif query.get('content'):
            return sorted(files, reverse=True, key=lambda x: fuzz.ratio(query['content'], x['content']))
        return files

    async def create_doc(self, messages: List[discord.Message] = [], filepath_to_metadata = {}, *args, **kwargs):
        """
        Update the search index for the corresponding server/channel with the new file.

        Args:
            messages: A list of messages that contain files
            message_attachments: A dict of filepaths to file metadata
        """
        if not filepath_to_metadata and not messages:
            return

        if messages:
            for message in messages:
                filepath = self.construct_index_file_path(message.channel)
                files = list(map(attachment_to_search_dict, message.attachments))
                existing_files = filepath_to_metadata.get(filepath, [])
                filepath_to_metadata[filepath] = existing_files.extend(files)

        for filepath in filepath_to_metadata:
            Path(filepath).mkdir(exist_ok=True)
            message_attachments = filepath_to_metadata[filepath]
            with open(filepath, 'a') as f:
                for file in message_attachments:
                    json.dump(file, f)
                    f.write(os.linesep)

    async def remove_doc(self, file_ids: list, *args, **kwargs):
        """Update banned ids with the file ids."""
        for file_id in file_ids:
            self.banned_file_ids.add(file_id)
