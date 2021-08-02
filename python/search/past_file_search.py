"""Search for files purely in discord."""
from .async_search_client import AsyncSearchClient
import discord
from typing import List, Dict
from fuzzywuzzy import fuzz
from utils import attachment_to_search_dict
import datetime


class PastFileSearch(AsyncSearchClient):
    """Search for files in discord with just discord."""

    def __init__(self, thresh: int = 85):
        """
        Create a DiscordSearch object.

        It's annoying to need bot_user but we do this to enable searching on files from other bots.

        Args:
            bot_user: The name of the bot user.
        """
        self.banned_file_ids = set()
        self.thresh = thresh
        self.user = None

    def initialize(self, bot_user: str, *args, **kwargs):
        """
        Initialize past file search.

        Args:
            bot_user: The bot username.
        """
        self.user = bot_user

    def match(self, message: discord.Message, filename: str, **kwargs) -> List[discord.Attachment]:
        """
        Match the message against possible arguments.

        Args:
            message: The message to test
            kwargs: kwargs of args to match

        Returns:
            A list of discord.Attachments that match the query.
        """
        if not message.attachments or message.author == self.user:
            return []
        if kwargs.get("content"):
            if fuzz.partial_ratio(kwargs['content'].lower(), message.content.lower()) < self.thresh:
                return []
        if kwargs.get("after"):
            if message.created_at < kwargs["after"]:
                return []
        if kwargs.get("before"):
            if message.created_at > kwargs["before"]:
                return []
        if kwargs.get("author"):
            if message.author != kwargs["author"]:
                return []
        if kwargs.get("channel"):
            if message.channel != kwargs["channel"]:
                return []
        # print(message.author, self.user, message.attachments[0].filename)

        res = filter(lambda atch: fuzz.partial_ratio(atch.filename.lower(),
                     filename.lower()) > self.thresh, message.attachments)
        if kwargs.get("mimetype"):
            return [attachment for attachment in res if attachment.content_type == kwargs["mimetype"]]
        if kwargs.get("banned_ids"):
            return [attachment for attachment in res if attachment.id not in kwargs["banned_ids"]]
        return list(res)

    async def search(self, filename: str, onii_chan, ctx_channel, *args, **kwargs) -> List[Dict]:
        """
        Iterate through previous messages in a discord channel for files.

        Args:
            filename: The query
            onii_chan: The channel to search in
            kawrgs: Search paramaters

        Returns:
            A list of dicts of files.
        """
        if self.user is None or not isinstance(filename, str):
            return ""
        files = []
        onii_chan = ctx_channel
        if kwargs.get("channel"):
            onii_chan = kwargs['channel']
        if kwargs.get("banned_ids"):
            kwargs['banned_ids'].update(self.banned_file_ids)
        else:
            kwargs['banned_ids'] = self.banned_file_ids

        if kwargs.get('after') is None:
            after = datetime.datetime.now() - datetime.timedelta(weeks=2)

        matched_messages = onii_chan.history(limit=int(1e9), before=kwargs.get("before"), after=after)
        async for message in matched_messages:
            matched = self.match(message, filename, **kwargs)
            files.extend([{**attachment_to_search_dict(message, atch), 'url': atch.url,
                         'jump_url': message.jump_url} for atch in matched])
        return files

    async def create_doc(self, *args, **kwargs):
        """We don't maintain search indices in this class, so this is not needed."""
        return

    async def remove_doc(self, file_ids: list, *args, **kwargs):
        """Update banned ids with the file ids."""
        self.banned_file_ids.add(tuple(file_ids))
        return
