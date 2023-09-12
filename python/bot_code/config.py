"""Stores the config variables."""

from dotenv.main import dotenv_values, find_dotenv
from types import SimpleNamespace

"""
DISCORD_TOKEN
GUILD_ID
TEST_DISCORD_TOKEN
DB_NAME
"""


class Config(SimpleNamespace):
    """Basic Config Manager."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __contains__(self, key):
        return key in self.__dict__


CONFIG = Config(**dotenv_values(find_dotenv()))

assert 'DISCORD_TOKEN' in CONFIG, "DISCORD_TOKEN must be set in .env"
