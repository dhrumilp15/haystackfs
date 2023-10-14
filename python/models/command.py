from dataclasses import dataclass
from datetime import datetime
from python.models.query import Query


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

        source = channel.guild.id if channel.guild is not None else channel.id
        return Command(
            caller=interaction.user.name,
            query=query,
            source=source,
            type=command_type,
            timestamp=datetime.now().isoformat()
        )
