"""Commonly used utility functions."""
from typing import List, Dict
from io import BytesIO
from discord.ext.commands.core import command
import requests
import discord
from discord.ext.commands import Bot
from datetime import datetime
import mongo_client as MgClient  # cyclic dependency

CONTENT_TYPE_CHOICES = [
    {"name": "mp4", "value": "video/mp4"},
    {"name": "gif", "value": "image/gif"},
    {"name": "jpg/jpeg", "value": "image/jpeg"},
    {"name": "pdf", "value": "application/pdf"},
    {"name": "png", "value": "image/png"},
    {"name": "image", "value": "image"},
    {"name": "audio", "value": "audio"},
    {"name": "zip", "value": "application/zip"},
    {"name": "mp3/m4a", "value": "audio/mpeg"},
    {"name": "OTHER", "value": "OTHER"}
]

PLZ_VERIFY = "Please verify this server at: https://forms.gle/UrhqHZNQhJHSdYpW7"


def filter_messages_with_permissions(
        author: discord.User,
        files: List[Dict],
        perm: discord.Permissions,
        bot: Bot) -> List[Dict]:
    """
    Filter messages that the `author` can view.

    Args:
        author: The discord.User querying for files
        files: A list of dicts returned from ElasticSearch.
        perm: The permission you're filtering with.

    Returns:
        A list of dicts of files from ElasticSearch that the author can view.
    """
    viewable_files = []
    for file in files:
        file_chan_id = int(file['channel_id'])
        file_message_chan = bot.get_channel(file_chan_id)
        if isinstance(file_message_chan, discord.DMChannel):
            viewable_files.append(file)
            continue
        authorperms = file_message_chan.permissions_for(author)
        # Question: What happens when a user is invited to a channel and has
        # the `read_messages` permission?
        # The user could only view messages posted *after* they were added.
        # If their query has images posted both before *and* after the user was
        # invited, what should we return?
        if authorperms >= perm:
            viewable_files.append(file)
    return viewable_files


async def download(files: List[Dict], mg_client: MgClient) -> List[discord.File]:
    """
    Download files from their urls (discord cdn).

    Args:
        files: A list of dicts of files from ElasticSearch.

    Returns:
        A list of discord.File objects of the files retrieved.
    """
    for file in files:
        file_id = file['objectID']
        try:
            res = await mg_client.get_file(file_id)
            # Found file in elasticsearch but not mongodb
            # This happens when testing results overlap with production results
            # since we use the same elasticsearch instance for production and
            # testing
            if not res:
                continue
        except BaseException as e:
            print(e)
        response = requests.get(res["url"], stream=True)
        if not response.ok:
            print(response)
        file_buf = BytesIO()
        for blk in response.iter_content(1024):
            if not blk:
                break
            file_buf.write(blk)
        file_buf.seek(0)
        yield discord.File(file_buf, res["file_name"])
        file_buf.close()


def attachment_to_search_dict(
        message: discord.Message,
        file: discord.Attachment) -> Dict:
    """
    Convert a discord.Attachment to the dict metadata format.

    The dict metadata format only contains searchable fields:
    - author id
    - message content
    - mimetype
    - message_id
    - channel_id

    Args:
        message: The discord.Message that contains this attachment
        file: The discord.Attachment to convert to a dict.

    Returns:
        A dict that contains metadata about the attachment.
    """
    body = {
        "objectID": file.id,
        "author_id": message.author.id,
        "content": message.content,
        "file_name": file.filename,
        "mimetype": file.content_type,
        "message_id": message.id,
        "channel_id": message.channel.id,
    }
    return body


def server_to_mongo_dict(
        server: discord.Guild or discord.DMChannel) -> Dict:
    """
    Convert a discord.Attachment to the dict metadata format.

    The dict metadata format only contains searchable fields:
    - author id
    - message content
    - created_at
    - mimetype
    - message_id

    Args:
        message: The discord.Message that contains this attachment
        file: The discord.Attachment to convert

    Returns:
        A dict that contains metadata about the attachment.
    """
    server_info = {
        "_id": server.id,
        "created_at": server.created_at,
        "owner_id": server.owner_id,
        "owner_name": server.owner.name + '#' + str(server.owner.discriminator),
        "members": server.member_count,
        "max_members": server.max_members,
        "description": server.description,
        "large": server.large,
        "name": server.name,
        "filesize_limit": server.filesize_limit,
        "icon": server.icon,
        "region": server.region,
        "timestamp": datetime.now(),
        "bot_in_server": True,
        "verified": False
    }
    return server_info


def attachment_to_mongo_dict(message: discord.Message,
                             file: discord.Attachment) -> Dict:
    """
    Convert a discord.Attachment to the dict metadata format.

    The dict metadata format only contains searchable fields:
    - author id
    - message content
    - created_at
    - mimetype
    - message_id

    Args:
        message: The discord.Message that contains this attachment
        file: The discord.Attachment to convert

    Returns:
        A dict that contains metadata about the attachment.
    """
    file_info = {
        "_id": file.id,
        "author": message.author.id,
        "author_name": message.author.name + '#' + str(message.author.discriminator),
        "channel_id": message.channel.id,
        "guild_id": message.guild.id if message.guild.id is not None else -1,
        "content": message.content,
        "created_at": message.created_at,
        "file_name": file.filename,
        "mimetype": file.content_type,
        "message_id": message.id,
        "size": file.size,
        "url": file.url,
        "height": file.height if file.height else -1,
        "width": file.width if file.width else -1,
        "timestamp": datetime.now()}
    return file_info
