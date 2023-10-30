from dataclasses import dataclass
import discord
from dateutil import parser
from datetime import datetime, timedelta
from dateutil.parser import ParserError
from ..messages import MALFORMED_DATE_STRING
from ..exceptions import QueryException


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
            try:
                before = parser.parse(self.before)
            except ParserError:
                raise QueryException(MALFORMED_DATE_STRING.format(self.before))
            before = datetime(*before.timetuple()[:3])
            before += timedelta(days=1) - timedelta(microseconds=1)
            self.before = before

        if self.after:
            try:
                after = parser.parse(self.after)
            except:
                raise QueryException(MALFORMED_DATE_STRING.format(self.after))
            after = datetime(*after.timetuple()[:3])
            after -= timedelta(microseconds=1)
            self.after = after

