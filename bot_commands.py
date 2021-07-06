"""The core functionality of the bot."""
from search_client import AsyncSearchClient
from mongo_client import MgClient
# from elasticsearch_client import ElasticSearchClient

import discord
from discord.ext import commands
from discord_slash import SlashContext
from typing import List, Dict

from utils import filter_messages_with_permissions, attachment_to_search_dict


async def fremove(ctx: SlashContext or commands.Context,
                  filename: str,
                  search_client: AsyncSearchClient,
                  mg_client: MgClient,
                  bot: commands.Bot) -> List[str]:
    """
    Remove files from ElasticSearch and MongoDB.

    Args:
        ctx: The message's origin
        filename: The query for files to remove
        search_client: The Search client
        mg_client: The MongoDB client
        bot: The discord bot

    Returns:
        A list of filenames that were deleted
    """
    author = ctx.author
    if not filename:
        return f"Couldn't process your query: `{filename}`"
    serv_id = ctx.channel.id
    if ctx.guild is not None:
        serv_id = ctx.guild.id

    files = await search_client.search(filename=filename, index=serv_id)

    manageable_files = filter_messages_with_permissions(
        author,
        files,
        discord.Permissions(read_message_history=True),
        bot
    )
    if not manageable_files:
        return f"I couldn't find any files related to `{filename}`"
    removed_files = []
    for file in manageable_files:
        await search_client.delete_doc(file_id=file['_id'], index=serv_id)
        res = await mg_client.remove_file(file['_id'])
        if res:
            removed_files.append(file['_source']['file_name'])
    return removed_files


async def fdelete(ctx: SlashContext or commands.Context,
                  filename: str,
                  search_client: AsyncSearchClient,
                  mg_client: MgClient,
                  bot: commands.Bot) -> List[str]:
    """
    Remove files from our storage and delete their corresponding discord messages.

    Args:
        ctx: The message's origin
        filename: The query for files to remove
        search_client: The Search client
        mg_client: The MongoDB client
        bot: The discord bot

    Returns:
        A list of filenames that were deleted
    """
    author = ctx.author
    if not filename:
        return f"Couldn't process your query: `{filename}`"

    if isinstance(
            ctx.channel,
            discord.DMChannel) or isinstance(
            ctx.channel,
            discord.GroupChannel):
        channel_id = ctx.channel.id
    else:
        channel_id = ctx.guild.id
    files = await search_client.search(filename=filename, index=channel_id)

    manageable_files = filter_messages_with_permissions(
        author,
        files,
        discord.Permissions(read_message_history=True),
        bot
    )
    if not manageable_files:
        return f"I couldn't find any files related to `{filename}`"

    deleted_files = []
    for file in manageable_files:
        await search_client.delete_doc(file_id=file['_id'], index=channel_id)
        res = await mg_client.remove_file(file['_id'])
        try:
            onii_chan = bot.get_channel(int(file['_source']['channel_id']))
            message = await onii_chan.fetch_message(
                file['_source']['message_id']
            )
            await message.delete()
            if res:
                deleted_files.append(file['_source']['file_name'])
        except discord.Forbidden:
            continue
    return deleted_files


async def fall(ctx: SlashContext or commands.Context,
               search_client: AsyncSearchClient,
               bot: commands.Bot) -> List[Dict]:
    """
    Find all docs in ElasticSearch.

    Args:
        ctx: The message's origin
        search_client: The Search client
        bot: The discord bot

    Returns:
        A list of dicts of viewable files.
    """
    try:
        author = ctx.author
        serv_id = ctx.channel.id
        if ctx.guild is not None:
            serv_id = ctx.guild.id
        files = await search_client.get_all_docs(serv_id)
        if not files:
            return "The archives are empty... Perhaps you could contribute..."
        if isinstance(files, str):
            return files
        manageable_files = filter_messages_with_permissions(
            author,
            files,
            discord.Permissions(read_message_history=True),
            bot
        )
        if not manageable_files:
            return "I couldn't find any files that you can access"
    except BaseException as e:
        print(e)
    return manageable_files


async def fsearch(ctx: SlashContext or commands.Context,
                  filename: str,
                  search_client: AsyncSearchClient,
                  bot: commands.Bot,
                  **kwargs) -> List[Dict]:
    """
    Find docs related to a query in ElasticSearch.

    Args:
        ctx: The message's origin
        filename: The query
        search_client: The Search client
        bot: The discord bot

    Returns:
        A list of dicts of viewable files.
    """
    if not filename:
        return f"Couldn't process your query: `{filename}`"

    onii_chan = ctx.channel
    if ctx.guild is not None:
        onii_chan = ctx.guild
    files = await search_client.search(
        filename=filename,
        serv_id=onii_chan.id,
        **kwargs
    )
    # past_files = await past_search(ctx, filename, bot, **kwargs)
    # files.extend(past_files)

    if not files:
        return f"I couldn't find any files related to your query"

    manageable_files = filter_messages_with_permissions(
        author=ctx.author,
        files=files,
        perm=discord.Permissions(read_message_history=True),
        bot=bot
    )
    if not manageable_files:
        return f"I couldn't find any files that you can access"
    return manageable_files


async def fclear(search_client: AsyncSearchClient, mg_client: MgClient, index: str):
    """
    Clear a channel or server id.

    Args:
        search_client: The Search client
        mg_client: The MongoDB client
        index: The index to clear
    """
    await search_client.clear(index)
    await mg_client.mass_remove_file(index)


def match(message: discord.Message, bot: commands.Bot, filename: str, **kwargs):
    """
    Match the message against possible arguments.

    Args:
        message: The message to test
        kwargs: kwargs of args to match

    Returns:
        True if the message matches
    """
    res = []
    if not message.attachments or message.author == bot.user:
        return []
    if kwargs.get("content"):
        if kwargs["content"] not in message.content:
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
    for attachment in message.attachments:
        if kwargs.get("mimetype"):
            if attachment.content_type != kwargs["mimetype"]:
                continue
        if filename in attachment.filename:
            res.append(attachment_to_search_dict(attachment))
    return res


async def past_search(
        ctx: SlashContext or commands.Context,
        filename: str,
        bot: commands.Bot,
        **kwargs) -> List[discord.Attachment]:
    """
    Iterate through previous messages in a discord channel for files.

    Args:
        ctx: The message's origin
        filename: The query
        bot: The discord bot

    Returns:
        A list of dicts of viewable files.
    """
    print(kwargs)
    files = []
    print("Started searching on previous files")
    matched_messages = await ctx.channel.history(limit=100, before=kwargs["before"], after=kwargs["after"]).flatten()
    print(f"Grabbed {len(matched_messages)} messages")
    for message in matched_messages:
        files.extend(match(message, bot=bot, filename=filename, kwargs=kwargs))
    return files
