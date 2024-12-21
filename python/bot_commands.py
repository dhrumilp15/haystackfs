"""The core functionality of the bot."""
from .models.query import Query
import discord
from .search.search_models import SearchResults
from .search.discord_searcher import DiscordSearcher
from .messages import NO_FILES_FOUND


async def fsearch(interaction: discord.Interaction, search_client: DiscordSearcher, query: Query) -> SearchResults:
    """
    Find docs related to a query in ElasticSearch.

    Args:
        interaction: The message's origin
        search_client: The Search client
        query: The query object

    Returns:
        A list of dicts of viewable files.
    """
    bot_user = None
    onii_chan = [interaction.channel if query.channel is None else query.channel]
    if interaction.guild is not None:
        bot_user = interaction.guild.me
        if not query.channel:
            forum_threads = [thread for channel in interaction.guild.forums for thread in channel.threads]
            onii_chan = interaction.guild.text_channels + forum_threads

    search_results = await search_client.search(
        onii_chans=onii_chan,
        bot_user=bot_user,
        query=query
    )
    if not search_results.files:
        return SearchResults(message=NO_FILES_FOUND)
    return search_results
