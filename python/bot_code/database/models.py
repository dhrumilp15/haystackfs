from dataclasses import dataclass
from datetime import datetime
from ..models.query import Query
import discord


@dataclass
class Command:
    caller: str
    query: Query
    source: str
    type: str
    timestamp: str

    @staticmethod
    def from_discord_interaction(command_type, interaction, query) -> 'Command':
        channel = interaction.channel

        source = channel.id
        if channel.guild is not None:
            source = channel.guild.id
        return Command(
            caller=interaction.user.name,
            query=query,
            source=source,
            type=command_type,
            timestamp=datetime.now().isoformat()
        )


@dataclass
class Attachment:
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
    def from_discord_message(message: discord.Message, file: discord.Attachment) -> 'Attachment':
        """
        Convert a discord.Attachment to the dict metadata format.

        The dict metadata format only contains searchable fields:
        - author id
        - message content
        - filetype
        - message_id
        - channel_id

        Args:
            message: The discord.Message that contains this attachment
            file: The discord.Attachment to convert to a dict.

        Returns:
            A dict that contains metadata about the attachment.
        """
        if '.' in file.filename:
            filetype = file.filename[file.filename.rindex('.') + 1:]
        else:
            filetype = "unknown"
        return Attachment(
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
