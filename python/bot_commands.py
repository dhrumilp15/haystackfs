"""The core functionality of the bot."""
from search.async_search_client import AsyncSearchClient
from mongo_client import MgClient
from utils import filter_messages_with_permissions

import discord
from discord.ext import commands
from typing import List, Dict


async def fremove(interaction: discord.Interaction or commands.Context,
                  search_client: AsyncSearchClient, mg_client: MgClient, bot: commands.Bot, **kwargs) -> List[str]:
    """
    Remove files from search and database.

    Args:
        interaction: The message's origin
        search_client: The Search client
        mg_client: The MongoDB client
        bot: The discord bot

    Returns:
        A list of filenames that were deleted
    """
    author = interaction.author
    serv_id = interaction.channel
    if interaction.guild is not None:
        serv_id = interaction.guild

    files = await search_client.search(serv_id, **kwargs)

    manageable_files = filter_messages_with_permissions(author=author, files=files,
                                                        perm=discord.Permissions(read_message_history=True), bot=bot)
    if not manageable_files:
        return f"I couldn't find any files that you can access."
    res = await search_client.remove_doc(
        [file['objectID'] for file in manageable_files],
        serv_id,
        author.name + "#" + author.discriminator
    )
    if not res.get('objectIDs'):
        return []
    res = await mg_client.remove_file([file['objectID'] for file in manageable_files])
    if not res:
        return []
    return manageable_files


async def fdelete(interaction: discord.Interaction or commands.Context, search_client: AsyncSearchClient,
                  mg_client: MgClient, bot: commands.Bot, **kwargs) -> List[str]:
    """
    Remove files from our storage and delete their corresponding discord messages.

    Args:
        interaction: The message's origin
        filename: The query for files to remove
        search_client: The Search client
        mg_client: The MongoDB client
        bot: The discord bot

    Returns:
        A list of filenames that were deleted
    """
    author = interaction.author
    serv_id = interaction.channel.id
    if interaction.guild is not None:
        serv_id = interaction.guild.id
    files = await search_client.search(serv_id, **kwargs)
    manageable_files = filter_messages_with_permissions(author=author, files=files,
                                                        perm=discord.Permissions(read_message_history=True), bot=bot)
    if not manageable_files:
        return f"I couldn't find any files that you can access."
    deleted_files = []
    await search_client.remove_doc(
        [file['objectID'] for file in manageable_files],
        serv_id,
        author.name + "#" + author.discriminator
    )
    await mg_client.remove_file([file['objectID'] for file in manageable_files])
    for file in manageable_files:
        try:
            onii_chan = bot.get_channel(int(file['channel_id']))
            message = await onii_chan.fetch_message(file['message_id'])
            await message.delete()
            deleted_files.append(file['filename'])
        except (discord.Forbidden, discord.errors.NotFound):
            continue
    return deleted_files


async def fsearch(interaction: discord.Interaction or commands.Context,
                  search_client: AsyncSearchClient,
                  bot: commands.Bot,
                  **kwargs) -> List[Dict]:
    """
    Find docs related to a query in ElasticSearch.

    Args:
        interaction: The message's origin
        filename: The query
        search_client: The Search client
        bot: The discord bot

    Returns:
        A list of dicts of viewable files.
    """
    onii_chan = [kwargs['channel']]
    if onii_chan[0] is None:
        onii_chan = interaction.channel
        if interaction.guild is not None:
            onii_chan = interaction.guild.text_channels

    bot_user = None
    if interaction.guild is not None:
        bot_user = interaction.guild.me

    files = await search_client.search(
        interaction,
        onii_chan,
        bot_user=bot_user,
        **kwargs
    )
    if not files:
        return f"I couldn't find any files related to your query. I may not have the `read_message_history` permission for some channels."

    return files
