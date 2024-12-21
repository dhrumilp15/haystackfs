"""Stores the config variables."""

from dotenv.main import load_dotenv
import os

load_dotenv()


def getenv(name: str, try_int: bool = False):
    var = os.getenv(name)
    if try_int:
        try:
            var = int(var)
        except:
            pass
    return var


DISCORD_TOKEN = getenv("DISCORD_TOKEN")
TEST_DISCORD_TOKEN = getenv("TEST_DISCORD_TOKEN")
DB_NAME = getenv("DB_NAME")
GUILD_ID = getenv("GUILD_ID", try_int=True)
SERVER_COUNT_CHANNEL_ID = getenv("SERVER_COUNT_CHANNEL_ID", try_int=True)
TEST_SERVER_COUNT_CHANNEL_ID = getenv("TEST_SERVER_COUNT_CHANNEL_ID", try_int=True)
ERROR_CHANNEL_ID = getenv("ERROR_CHANNEL_ID", try_int=True)
SEARCH_METRICS_CHANNEL_ID = getenv("SEARCH_METRICS_CHANNEL_ID", try_int=True)
EXPORT_METRICS_CHANNEL_ID = getenv("EXPORT_METRICS_CHANNEL_ID", try_int=True)
DELETE_METRICS_CHANNEL_ID = getenv("DELETE_METRICS_CHANNEL_ID", try_int=True)
TEST_SEARCH_METRICS_CHANNEL_ID = getenv("TEST_SEARCH_METRICS_CHANNEL_ID", try_int=True)
TEST_EXPORT_METRICS_CHANNEL_ID = getenv("TEST_EXPORT_METRICS_CHANNEL_ID", try_int=True)
TEST_DELETE_METRICS_CHANNEL_ID = getenv("TEST_DELETE_METRICS_CHANNEL_ID", try_int=True)

assert ERROR_CHANNEL_ID
if DB_NAME == "testing":
    assert TEST_DISCORD_TOKEN
    assert TEST_SEARCH_METRICS_CHANNEL_ID
    assert TEST_EXPORT_METRICS_CHANNEL_ID
    assert TEST_DELETE_METRICS_CHANNEL_ID
else:
    assert DISCORD_TOKEN
    assert SEARCH_METRICS_CHANNEL_ID
    assert EXPORT_METRICS_CHANNEL_ID
    assert DELETE_METRICS_CHANNEL_ID

METRICS_CHANNEL_MAP = dict(
    testing=dict(
        search=TEST_SEARCH_METRICS_CHANNEL_ID,
        export=TEST_EXPORT_METRICS_CHANNEL_ID,
        delete=TEST_DELETE_METRICS_CHANNEL_ID,
        server_count=TEST_SERVER_COUNT_CHANNEL_ID
    ),
    production=dict(
        search=SEARCH_METRICS_CHANNEL_ID,
        export=EXPORT_METRICS_CHANNEL_ID,
        delete=DELETE_METRICS_CHANNEL_ID,
        server_count=SERVER_COUNT_CHANNEL_ID
    )
)
