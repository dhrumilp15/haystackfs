from dataclasses import dataclass
import discord



@dataclass
class Query:
    filename: str = None
    filetype: str = None
    custom_filetype: str = None
    author: discord.User = None
    channel: discord.TextChannel = None
    content: str = None
    after: str = None
    before: str = None
    dm: bool = False
