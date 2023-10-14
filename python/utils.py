"""Commonly used utility functions."""
import discord


CONTENT_TYPE_CHOICES = sorted([
    dict(name="mp4", value="video/mp4"),
    dict(name="gif", value="image/gif"),
    dict(name="jpg/jpeg", value="image/jpeg"),
    dict(name="pdf", value="application/pdf"),
    dict(name="png", value="image/png"),
    dict(name="image", value="image"),
    dict(name="audio", value="audio"),
    dict(name="zip", value="application/zip"),
    dict(name="mp3/m4a", value="audio/mpeg"),
], key=lambda x: x['name'])
CONTENT_TYPE_CHOICES = list(map(lambda opt: discord.app_commands.Choice(**opt), CONTENT_TYPE_CHOICES))

dm_option = dict(
    name="dm",
    description="If `True`, I'll dm you what I find. Otherwise, I'll send it to this channel",
    option_type=discord.AppCommandOptionType.boolean,
    required=False
)

search_options = [
    {
        "name": "filename",
        "description": "Even a partial name of your file will do :)",
        "option_type": discord.AppCommandOptionType.string,
        "required": False,
    },
    {
        "name": "filetype",
        "description": "You can choose a filetype here. Use `custom filetype` to specify a different one",
        "option_type": discord.AppCommandOptionType.string,
        "required": False,
        "choices": CONTENT_TYPE_CHOICES
    },
    {
        "name": "custom_filetype",
        "description": "Searches for files of a custom file type",
        "option_type": discord.AppCommandOptionType.string,
        "required": False,
    },
    {
        "name": "author",
        "description": "Searches for files uploaded by a user",
        "option_type": discord.AppCommandOptionType.user,
        "required": False
    },
    {
        "name": "channel",
        "description": "Searches for files in a channel",
        "option_type": discord.AppCommandOptionType.channel,
        "required": False
    },
    {
        "name": "content",
        "description": "Search for files in messages by message content",
        "option_type": discord.AppCommandOptionType.string,
        "required": False
    },
    {
        "name": "after",
        "description": "Search for files after a date. Use the `before` option to specify a range of dates",
        "option_type": discord.AppCommandOptionType.string,
        "required": False
    },
    {
        "name": "before",
        "description": "Search for files before a date. Use the `after` option to specify a range of dates",
        "option_type": discord.AppCommandOptionType.string,
        "required": False
    },
    dm_option
]

search_opts = {opt['name']: opt['description'] for opt in search_options}
