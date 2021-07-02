"""Stores the config variables."""

from dotenv.main import dotenv_values, find_dotenv
from types import SimpleNamespace

"""
DISCORD_TOKEN
ELASTIC_DOMAIN
ELASTIC_PORT
GUILD_ID
TEST_DISCORD_TOKEN
MONGO_USER
MONGO_PASSWD
MONGO_ENDPOINT
DB_NAME
ALGOLIA_APP_ID
ALGOLIA_SEARCH_KEY
ALGOLIA_ADMIN_KEY
"""
CONFIG = SimpleNamespace(**dotenv_values(find_dotenv()))
