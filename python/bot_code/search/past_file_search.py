"""Search for files purely in discord."""
from .async_search_client import AsyncSearchClient
import discord
from typing import List, Dict, Union
from fuzzywuzzy import fuzz
from utils import attachment_to_mongo_dict, attachment_to_search_dict
from pathlib import Path
import asyncio
import aiofiles
import os
import msgpack


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
        self.ext = ".msgpack"
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
                yield map(lambda atchmt: attachment_to_search_dict(message, atchmt), message.attachments)

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
        filepath = str(source)
        if onii_chan.guild is not None:
            filepath = os.path.join(str(onii_chan.guild.id), filepath)
        filepath = os.path.join(self.indices_fp, filepath)
        filepath += self.ext
        return filepath

    async def channel_index_writer(self, onii_chan: discord.TextChannel):
        filepath = self.construct_index_file_path(onii_chan)
        if not os.path.exists(filepath):
            buffer = {filepath: []}
            channel_file_set = set()
            async for file_attachments in self.channel_index(onii_chan):
                for file in file_attachments:
                    if file['objectID'] in channel_file_set:
                        continue
                    channel_file_set.add(file['objectID'])
                    existing_files = buffer.get(filepath, [])
                    if len(existing_files) >= self.write_buffer_size:
                        await self.create_doc(filepath_to_metadata=buffer)
                        buffer[filepath] = []
                        channel_file_set = set()
                    existing_files.append(file)
                    buffer[filepath] = existing_files
            await self.create_doc(filepath_to_metadata=buffer)

    async def load_index(self, interaction: discord.Interaction, onii_chans: List[discord.TextChannel]):
        """
        Builds indices for the target channels if needed

        Args:
            interaction: The original interaction that created the search request
            onii_chans: The source text channels
        """
        not_indexed_channels = []
        for onii_chan in onii_chans:
            filepath = self.construct_index_file_path(onii_chan=onii_chan)
            if not os.path.exists(filepath):
                not_indexed_channels.append(onii_chan)
        if not_indexed_channels:
            await interaction.followup.send("I haven't indexed this channel/server yet and may take a while to respond.")

        tasks = []
        for onii_chan in not_indexed_channels:
            tasks.append(asyncio.ensure_future(self.channel_index_writer(onii_chan)))

        await asyncio.gather(*tasks)

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
        filepath = self.construct_index_file_path(onii_chan=onii_chan)
        # this channel has no attachments
        if not os.path.exists(filepath):
            return []
        files = []
        files_set = set()
        with open(filepath, 'rb') as f:
            unpacker = msgpack.Unpacker(f)
            for metadata in unpacker:
                if metadata['objectID'] in self.banned_file_ids or metadata['objectID'] in files_set:
                    continue
                if search_dict_match(metadata=metadata, thresh=self.thresh, **query):
                    files.append(metadata)
                    files_set.add(metadata['objectID'])
        return files, files_set

    async def search(self, interaction: discord.Interaction, onii_chans: List[Union[discord.DMChannel, discord.Guild]], bot_user=None, **query) -> List[Dict]:
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
        await self.load_index(interaction, onii_chans)

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
            dir_name = os.path.dirname(filepath)
            Path(dir_name).mkdir(exist_ok=True)
            message_attachments = filepath_to_metadata[filepath]
            mode = 'ab'
            if not os.path.exists(filepath):
                mode = 'wb'
            async with aiofiles.open(filepath, mode=mode) as f:
                for file in message_attachments:
                    packed = msgpack.packb(file)
                    await f.write(packed)

    async def remove_doc(self, file_ids: list, *args, **kwargs):
        """Update banned ids with the file ids."""
        for file_id in file_ids:
            self.banned_file_ids.add(file_id)
