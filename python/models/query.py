import json
from dataclasses import dataclass
import discord
from dateutil import parser
from datetime import datetime, timedelta
from dateutil.parser import ParserError


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
    channel_date_map: dict[str, datetime] = None

    def __post_init__(self):
        # Lazy import to avoid pulling in the full discord/bot_secrets graph
        # at module load time — keeps Query importable for unit tests.
        from ..messages import MALFORMED_DATE_STRING
        from ..exceptions import QueryException

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

    def to_json(self) -> str:
        """Serialize for the persistent pagination store.

        Stores discord objects as bare ids and datetimes as ISO strings.
        """
        def _dt(v):
            return v.isoformat() if isinstance(v, datetime) else v

        cdm = None
        if self.channel_date_map:
            cdm = {
                k: (v.isoformat() if isinstance(v, datetime) else v)
                for k, v in self.channel_date_map.items()
            }
        return json.dumps({
            "filename": self.filename,
            "filetype": self.filetype,
            "custom_filetype": self.custom_filetype,
            "author_id": self.author.id if self.author else None,
            "channel_id": self.channel.id if self.channel else None,
            "content": self.content,
            "after": _dt(self.after),
            "before": _dt(self.before),
            "dm": self.dm,
            "channel_date_map": cdm,
        })

    @classmethod
    def from_json(cls, blob: str, *, bot) -> "Query":
        """Rehydrate from to_json output WITHOUT running __post_init__.

        __post_init__ shifts `after` backwards by one day each time it runs on
        an already-shifted value (it truncates to date components and then
        subtracts another microsecond). Bypassing it via __new__ keeps the
        cursor stable across round-trips.
        """
        d = json.loads(blob)
        obj = cls.__new__(cls)
        obj.filename = d.get("filename")
        obj.filetype = d.get("filetype")
        obj.custom_filetype = d.get("custom_filetype")
        author_id = d.get("author_id")
        channel_id = d.get("channel_id")
        obj.author = bot.get_user(author_id) if author_id else None
        obj.channel = bot.get_channel(channel_id) if channel_id else None
        obj.content = d.get("content")
        obj.after = datetime.fromisoformat(d["after"]) if d.get("after") else None
        obj.before = datetime.fromisoformat(d["before"]) if d.get("before") else None
        obj.dm = d.get("dm", False)
        cdm = d.get("channel_date_map")
        if cdm:
            cdm = {
                k: (datetime.fromisoformat(v) if isinstance(v, str) else v)
                for k, v in cdm.items()
            }
        obj.channel_date_map = cdm
        return obj

