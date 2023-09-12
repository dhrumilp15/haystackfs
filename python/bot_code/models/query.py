from dataclasses import dataclass
import discord
from dateutil import parser
from datetime import datetime, timedelta


@dataclass
class Query:
    filename: str = None
    filetype: str = None
    custom_filetype: str = None
    author: discord.User = None
    channel: discord.TextChannel = None
    content: str = None
    after: str or datetime = None
    before: str or datetime = None
    dm: bool = False

    def __post_init__(self):
        if self.before:
            before = parser.parse(self.before)
            before = datetime(*before.timetuple()[:3])
            before += timedelta(days=1) - timedelta(microseconds=1)
            self.before = before

        if self.after:
            after = parser.parse(self.after)
            after = datetime(*after.timetuple()[:3])
            after -= timedelta(microseconds=1)
            self.after = after

