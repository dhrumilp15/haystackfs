"""Commonly used utility functions."""
from typing import List, Dict
from io import BytesIO
import requests
import discord
from discord.ext.commands import Bot
from datetime import datetime
import mongo_client as MgClient  # cyclic dependency
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option

CONTENT_TYPE_CHOICES = sorted([
    {"name": "mp4", "value": "video/mp4"},
    {"name": "gif", "value": "image/gif"},
    {"name": "jpg/jpeg", "value": "image/jpeg"},
    {"name": "pdf", "value": "application/pdf"},
    {"name": "png", "value": "image/png"},
    {"name": "image", "value": "image"},
    {"name": "audio", "value": "audio"},
    {"name": "zip", "value": "application/zip"},
    {"name": "mp3/m4a", "value": "audio/mpeg"},

], key=lambda x: x['name']) + [{"name": "OTHER", "value": "OTHER"}]

search_options = [
    create_option(
        name="filename",
        description="Even a partial name of your file will do :)",
        option_type=SlashCommandOptionType.STRING,
        required=True,
    ),
    create_option(
        name="filetype",
        description="You can choose a filetype here. Use `custom filetype` to specify a different one",
        option_type=SlashCommandOptionType.STRING,
        required=False,
        choices=CONTENT_TYPE_CHOICES
    ),
    create_option(
        name="custom_filetype",
        description="Searches for files of a custom file type",
        option_type=SlashCommandOptionType.STRING,
        required=False,
    ),
    create_option(
        name="author",
        description="Searches for files uploaded by a user",
        option_type=SlashCommandOptionType.USER,
        required=False
    ),
    create_option(
        name="channel",
        description="Searches for files in a channel",
        option_type=SlashCommandOptionType.CHANNEL,
        required=False
    ),
    create_option(
        name="content",
        description="Search for files in messages by message content",
        option_type=SlashCommandOptionType.STRING,
        required=False
    ),
    create_option(
        name="after",
        description="Search for files after a date. \
                Use the `before` option to specify a range of dates",
        option_type=SlashCommandOptionType.STRING,
        required=False
    ),
    create_option(
        name="before",
        description="Search for files before a date. \
                Use the `after` option to specify a range of dates",
        option_type=SlashCommandOptionType.STRING,
        required=False
    ),
    create_option(
        name="dm",
        description="If `True`, I'll dm you what I find. \
                Otherwise, I'll send it to this channel",
        option_type=SlashCommandOptionType.BOOLEAN,
        required=False,
    ),
]

PLZ_VERIFY = "Please verify this server at: https://forms.gle/UrhqHZNQhJHSdYpW7"


def filter_messages_with_permissions(author: discord.User, files: List[Dict], perm: discord.Permissions, bot: Bot) -> List[Dict]:
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
        url = file.get('url')
        filename = file.get('file_name')
        if not url:
            file_id = file['objectID']
            try:
                res = await mg_client.get_file(file_id)
                if not res:
                    print("Empty response from Mongo")
                    continue
                url = res['url']
                filename = res['file_name']
            except BaseException as e:
                print(e)
        response = requests.get(url, stream=True)
        if not response.ok:
            print(response)
        file_buf = BytesIO()
        for blk in response.iter_content(1024):
            if not blk:
                break
            file_buf.write(blk)
        file_buf.seek(0)
        yield discord.File(file_buf, filename)
        file_buf.close()


def attachment_to_search_dict(message: discord.Message, file: discord.Attachment) -> Dict:
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


def server_to_mongo_dict(server: discord.Guild or discord.DMChannel) -> Dict:
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


def attachment_to_mongo_dict(message: discord.Message, file: discord.Attachment) -> Dict:
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


# async def send_files_as_message(author: discord.User or SlashContext, files: List[Dict], mg_client: MgClient):
#     """
#     Send files to the author of the message.

#     Args:
#         author: The author or SlashContext of the search query
#         files: A list of dicts of files returned from ElasticSearch
#     """
#     async for file in download(files, mg_client):
#         await author.send(file=file)
#         file.close()
