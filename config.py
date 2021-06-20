"""Stores the config variables."""

from dotenv.main import dotenv_values


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
"""
CONFIG = dotenv_values(".env")
# CONFIG = {k: try_int(v) for k, v in dotenv_values(".env").items()}
