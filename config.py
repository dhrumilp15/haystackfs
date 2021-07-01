"""Stores the config variables."""

from dotenv.main import dotenv_values
from types import SimpleNamespace


# def try_int(value: str):
#     """Try to make the value an int.

#     Arguments:
#         value: The value to attempt to convert to an integer

#     Returns:
#         The value as an integer (if `int` can be applied). Otherwise a str
#     """
#     try:
#         return int(value)
#     except ValueError:
#         return value


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
CONFIG = SimpleNamespace(**dotenv_values(".env"))
