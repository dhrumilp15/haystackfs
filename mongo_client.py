"""MongoDB Client."""
import logging
from pymongo import MongoClient
from pymongo.results import InsertOneResult
from config import CONFIG
import discord
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s: {%(filename)s:%(funcName)s:%(lineno)d} - %(levelname)s: %(message)s',
    filename='out.log',
    level=logging.DEBUG)


class MgClient:
    """MongoDB Client."""

    def __init__(self):
        """Initialize the MongoDB Client and database."""
        self.client = MongoClient(CONFIG["MONGO_ENDPOINT"])
        self.db = self.client[CONFIG["DB_NAME"]]
        logger.info(f"Connected to MongoDB! Current database: {self.db.name}")

    def add_server(self, server: discord.Guild or discord.DMChannel):
        """
        Add a server or channel to the `servers` collection.

        Args:
            server: The server or DMChannel to add to the collection

        Returns:
            Whether the insert operation was successful
        """
        server_coll = self.db.servers
        # We've already added the server
        if server_coll.count_documents({"_id": server.id}, limit=1):
            return True
        server_info = {
            "_id": server.id,
            "created_at": server.created_at,
            "owner_id": server.owner_id,
            "owner_name": server.owner.name + '#' + str(server.owner.discriminator),
            "members": server.member_count,
            "max_members": server.max_members,
            "description": server.description,
            "large": server.large,
            "name": server.name,
            "filesize_limit": server.filesize_limit,
            "icon": server.icon,
            "region": server.region,
            "timestamp": datetime.now(),
            "bot_in_server": True,
        }
        res = server_coll.insert_one(server_info)
        if res.acknowledged:
            logger.info(
                f"Inserted new server: {res.inserted_id} with server id: {server.id}")
        else:
            logger.error(
                f"Failed to insert new server: {res.inserted_id} with server id: {server.id}")
        return res.acknowledged

    def add_file(self, message: discord.Message) -> int:
        """
        Add a file to the `files` collection.

        Args:
            message: The discord.Message containing the files.

        Returns:
            The number of files in the message successfully inserted into the collection
        """
        files_coll = self.db.files
        files_added = 0
        # We've already added the files in this message id
        if files_coll.count_documents({"message_id": message.id}, limit=1):
            return True

        for file in message.attachments:
            # We've already added this file
            if files_coll.count_documents({"_id": file.id}, limit=1):
                return True
            file_info = {
                "_id": file.id,
                "author": message.author.id,
                "author_name": message.author.name + '#' + str(message.author.discriminator),
                "channel_id": message.channel.id,
                "guild_id": message.guild.id if message.guild.id is not None else -1,
                "content": message.content,
                "created_at": message.created_at,
                "file_name": file.filename,
                "mimetype": file.content_type,
                "message_id": message.id,
                "size": file.size,
                "url": file.url,
                "height": file.height if file.height else -1,
                "width": file.width if file.width else -1,
                "timestamp": datetime.now()}

            res = files_coll.insert_one(file_info)
            if res.acknowledged:
                logger.info(
                    f"Inserted new file: {res.inserted_id} with file id: {file.id}")
                files_added += 1
            else:
                logger.error(
                    f"Failed to insert new file: {res.inserted_id} with file id: {file.id}")
        return files_added

    def remove_file(self, file_id: str):
        """
        Remove a file.

        Args:
            file: The id of the file to remove

        Returns:
            Whether the file was succesfully removed.
        """
        files_coll = self.db.files
        res = files_coll.delete_one({"_id": file_id})
        if res.acknowledged:
            logger.info(
                f"Deleted file: {res.inserted_id} with file id: {file_id}")
        else:
            logger.error(
                f"Failed to delete new file: {res.inserted_id} with file id: {file_id}")
        return res.acknowledged

    def mass_remove_file(self, serv_id: str):
        """
        Remove a file.

        Args:
            file: The id of the file to remove

        Returns:
            Whether the file was succesfully removed.
        """
        files_coll = self.db.files
        res = files_coll.delete_many({"channel_id": serv_id})
        res = files_coll.delete_many({"guild_id": serv_id})
        if res.acknowledged:
            logger.info(
                f"Deleted files: {res.inserted_id} with server/channel id: {serv_id}")
        else:
            logger.error(
                f"Failed to delete new file: {res.inserted_id} with server/channel id: {serv_id}")
        return res.acknowledged


if __name__ == '__main__':
    MgClient()
