from dataclasses import dataclass, fields
from typing import List
from ..models.query import Query
from thefuzz import fuzz
from datetime import datetime


@dataclass
class SearchResult:
    objectId: int
    author_id: int
    content: str
    filename: str
    content_type: str
    filetype: str
    channel_id: int
    message_id: int
    url: str
    jump_url: str
    created_at: str

    @staticmethod
    def from_discord_attachment(message, file) -> 'SearchResult':
        if '.' in file.filename:
            filetype = file.filename[file.filename.rindex('.') + 1:]
        else:
            filetype = "unknown"
        return SearchResult(
            objectId=file.id,
            author_id=message.author.id,
            content=message.content,
            filename=file.filename,
            content_type=file.content_type,
            filetype=filetype,
            channel_id=message.channel.id,
            message_id=message.id,
            url=file.url,
            jump_url=message.jump_url,
            created_at=message.created_at.isoformat()
        )

    def match_query(self, query: Query, thresh):
        query_fields = list(filter(lambda field: getattr(query, field.name), fields(query)))
        for field in query_fields:
            key = field.name
            value = getattr(query, key)
            if key == "content" or key == "filename" or key == "custom_filetype":
                if key == "custom_filetype":
                    key = "filetype"
                score = fuzz.partial_ratio(value.lower(), getattr(self, key).lower())
                if score < thresh:
                    return False
            elif key == "after":
                created_at = datetime.fromisoformat(self.created_at)
                created_at = created_at.replace(tzinfo=None)
                if created_at < value:
                    return False
            elif key == "before":
                created_at = datetime.fromisoformat(self.created_at)
                created_at = created_at.replace(tzinfo=None)
                if created_at > value:
                    return False
            elif key == "author" or key == "channel":
                if getattr(self, key + "_id") != value.id:
                    return False
            elif key == "filetype":
                filetype = self.content_type
                if filetype is None:
                    value = value[value.index('/') + 1:]
                    filetype = self.filetype
                if value == 'image' and not self.is_image():
                    return False
                if value == 'audio' and not self.is_audio():
                    return False
                if value != filetype:
                    return False
        return True

    def is_image(self):
        if not self.content_type:
            return False
        if 'image' in self.content_type:
            return True
        return self.filetype in {'jpg', 'jpeg', 'gif', 'png'}

    def is_audio(self):
        if not self.content_type:
            return False
        if 'audio' in self.content_type:
            return True
        return self.filetype in {'wav', 'mp3'}


@dataclass
class SearchResults:
    files: List[SearchResult] = None
    message: str = ""
    channel_date_map: dict = None

    @staticmethod
    def from_discord_message(message) -> 'SearchResults':
        files: List[SearchResult] = []
        for attachment in message.attachments:
            files.append(SearchResult.from_discord_attachment(message, attachment))
        return SearchResults(files=files)
