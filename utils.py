from typing import List, Dict
from io import BytesIO
import requests
import discord


def filter_messages_with_permissions(
        author: discord.User,
        files: List[Dict],
        perm: discord.Permissions,
        bot: discord.ext.commands.Bot) -> List[Dict]:
    """Finds the messages that the `author` can view

    Args:
        author: The discord.User querying for files
        files: A list of dicts returned from ElasticSearch.
        perm: The permission you're filtering with.

    Returns:
        A list of dicts of files from ElasticSearch that the author can view.
    """
    viewable_files = []
    for file in files:
        file_chan_id = int(file['_source']['channel_id'])
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


def download(files: List[Dict]) -> List[discord.File]:
    """Downloads files from their urls (discord cdn)

    Args:
        files: A list of dicts of files from ElasticSearch.

    Returns:
        A list of discord.File objects of the files retrieved.
    """
    filebufs = []
    for file in files:
        url = file['_source']['url']
        response = requests.get(url, stream=True)
        if not response.ok:
            print(response)
        file_buf = BytesIO()
        for blk in response.iter_content(1024):
            if not blk:
                break
            file_buf.write(blk)
        file_buf.seek(0)
        filebufs.append(discord.File(file_buf, file['_source']['file_name']))
    return filebufs
