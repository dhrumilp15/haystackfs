from typing import List, Dict

import discord
from discord.ext import commands
from discord_slash import SlashContext
from elasticsearch_client import ElasticSearchClient
from datetime import datetime

from utils import filter_messages_with_permissions


async def fremove(ctx: SlashContext or commands.Context,
                  filename: str,
                  es_client: ElasticSearchClient,
                  bot: commands.Bot) -> List[str]:
    """Removes files from ElasticSearch

    Args:
        ctx: The message's origin
        filename: The query for files to remove
        es_client: The ElasticSearch client
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
    files = es_client.search(filename=filename, index=channel_id)

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
        es_client.delete_doc(file_id=file['_id'], index=channel_id)
        removed_files.append(file['_source']['file_name'])
    return removed_files


async def fdelete(ctx: SlashContext or commands.Context,
                  filename: str,
                  es_client: ElasticSearchClient,
                  bot: commands.Bot) -> List[str]:
    """Removes files from ElasticSearch and deletes their respective discord
    messages.

    Args:
        ctx: The message's origin
        filename: The query for files to remove
        es_client: The ElasticSearch client
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
    files = es_client.search(filename=filename, index=channel_id)

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
        es_client.delete_doc(file_id=file['_id'], index=channel_id)
        try:
            onii_chan = bot.get_channel(int(file['_source']['channel_id']))
            message = await onii_chan.fetch_message(
                file['_source']['message_id']
            )
            await message.delete()
            deleted_files.append(file['_source']['file_name'])
        except discord.Forbidden:
            continue
    return deleted_files


async def fall(ctx: SlashContext or commands.Context,
               es_client: ElasticSearchClient,
               bot: commands.Bot) -> List[Dict]:
    """Finds all docs in ElasticSearch

    Args:
        ctx: The message's origin
        es_client: The ElasticSearch client
        bot: The discord bot

    Returns:
        A list of dicts of viewable files.
    """
    author = ctx.author
    if isinstance(
            ctx.channel,
            discord.DMChannel) or isinstance(
            ctx.channel,
            discord.GroupChannel):
        files = es_client.get_all_docs(ctx.channel.id)
    else:
        files = es_client.get_all_docs(ctx.guild.id)
    if not files:
        return "The archives are empty..."
    manageable_files = filter_messages_with_permissions(
        author,
        files,
        discord.Permissions(read_message_history=True),
        bot
    )
    if not manageable_files:
        return "I couldn't find any files that you can access"
    return manageable_files


async def fsearch(ctx: SlashContext or commands.Context,
                  filename: str,
                  es_client: ElasticSearchClient,
                  bot: commands.Bot,
                  mimetype: str = None,
                  author: discord.User = None,
                  channel: discord.channel = None,
                  content: str = None,
                  after: datetime = None,
                  before: datetime = None,
                  ) -> List[Dict]:
    """Finds docs related to a query in ElasticSearch

    Args:
        ctx: The message's origin
        filename: The query
        es_client: The ElasticSearch client
        bot: The discord bot

    Returns:
        A list of dicts of viewable files.
    """

    if not filename:
        return f"Couldn't process your query: `{filename}`"

    onii_chan = ctx.channel
    if ctx.guild is not None:
        onii_chan = ctx.guild
    files = es_client.search(
        filename=filename,
        index=onii_chan.id,
        filetype=mimetype,
        author=author,
        channel=channel,
        content=content,
        after=after,
        before=before
    )
    if not files:
        return f"I couldn't find any files related to your query"

    manageable_files = filter_messages_with_permissions(
        ctx.author,
        files,
        discord.Permissions(read_message_history=True),
        bot
    )
    if not manageable_files:
        return f"I couldn't find any files that you can access"
    return manageable_files


async def fclear(es_client: ElasticSearchClient, index: str):
    es_client.clear_index(index)
