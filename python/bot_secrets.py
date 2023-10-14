"""Stores the config variables."""

from dotenv.main import load_dotenv
import os

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TEST_DISCORD_TOKEN = os.getenv("TEST_DISCORD_TOKEN", None)
GUILD_ID = os.getenv("GUILD_ID")
ERROR_CHANNEL_ID = os.getenv("ERROR_CHANNEL_ID")
GUILD_ID = int(GUILD_ID) if GUILD_ID is not None else GUILD_ID
ERROR_CHANNEL_ID = int(ERROR_CHANNEL_ID) if ERROR_CHANNEL_ID is not None else ERROR_CHANNEL_ID
DB_NAME = os.getenv("DB_NAME")

assert DISCORD_TOKEN
assert ERROR_CHANNEL_ID
