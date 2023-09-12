"""The core functionality of the bot."""
from .models.query import Query
import discord
from discord.ext import commands
from typing import List
from .search.async_search_client import AsyncSearchClient
from .search.search_models import SearchResults
from .messages import NO_FILES_FOUND


async def fdelete(interaction: discord.Interaction or commands.Context, search_client: AsyncSearchClient,
                  bot: commands.Bot, query: Query) -> List[str]:
    """
    Remove files from our storage and delete their corresponding discord messages.

    Args:
        interaction: The message's origin
        search_client: The Search client
        bot: The discord bot
        query: The search query

    Returns:
        A list of filenames that were deleted
    """
    serv_id = interaction.channel.id
    if interaction.guild is not None:
        serv_id = interaction.guild.id
    files = await search_client.search(serv_id, query=query)
    deleted_files = []
    for file in files.files:
        try:
            onii_chan = bot.get_channel(int(file.channel_id))
            message = await onii_chan.fetch_message(file.message_id)
            await message.delete()
            deleted_files.append(file.filename)
        except (discord.Forbidden, discord.errors.NotFound):
            continue
    return deleted_files


async def fsearch(interaction: discord.Interaction or commands.Context,
                  search_client: AsyncSearchClient,
                  query: Query) -> SearchResults:
    """
    Find docs related to a query in ElasticSearch.

    Args:
        interaction: The message's origin
        search_client: The Search client
        query: The query object

    Returns:
        A list of dicts of viewable files.
    """
    onii_chan = [query.channel]
    if query.channel is None:
        onii_chan = interaction.channel
        if interaction.guild is not None:
            onii_chan = interaction.guild.text_channels

    bot_user = None
    if interaction.guild is not None:
        bot_user = interaction.guild.me

    search_results = await search_client.search(
        interaction,
        onii_chan,
        bot_user=bot_user,
        query=query
    )
    if not search_results.files:
        return SearchResults(message=NO_FILES_FOUND)
    return search_results
