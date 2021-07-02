"""MongoDB Client."""
import logging
import motor.motor_asyncio
import discord
from typing import List, Dict

from config import CONFIG
import utils
# import utils.server_to_mongo_dict as server_to_mongo_dict
# import utils.attachment_to_mongo_dict as attachment_to_mongo_dict

logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s: {%(filename)s:%(funcName)s:%(lineno)d} - %(levelname)s: %(message)s',
    filename='mg_client.log',
    level=logging.DEBUG)


class MgClient:
    """MongoDB Client."""

    def __init__(self):
        """Initialize the MongoDB Client and database."""
        self.client = motor.motor_asyncio.AsyncIOMotorClient(
            CONFIG.MONGO_ENDPOINT)
        self.db = self.client[CONFIG.DB_NAME]
        logger.info(f"Connected to MongoDB! Current database: {self.db.name}")

    async def get_file(self, file_id: int) -> dict:
        """
        Get the file url of the file id.

        Args:
            file_id: The id of the file to retrieve.

        Returns:
            The file url as a str.
        """
        res = await self.db.files.find_one(
            {"_id": int(file_id)},
            {"url": 1, "file_name": 1}
        )
        return res

    async def add_server(self, server: discord.Guild or discord.DMChannel):
        """
        Add a server or channel to the `servers` collection.

        Args:
            server: The server or DMChannel to add to the collection

        Returns:
            Whether the insert operation was successful
        """
        server_coll = self.db.servers
        # We've already added the server
        num_docs = await server_coll.count_documents({"_id": server.id}, limit=1)
        if num_docs:
            return True
        server_info = utils.server_to_mongo_dict(server)
        res = await server_coll.insert_one(server_info)
        if res.acknowledged:
            logger.info(
                f"Inserted new server: {res.inserted_id} with server id: {server.id}")
        else:
            logger.error(
                f"Failed to insert new server with server _id: {server.id}")
        return res.acknowledged

    async def remove_server(self, server_id: int) -> bool:
        """
        Mark the bot as not in this server.

        Args:
            guild: The guild to remove the bot from.

        Returns:
            Whether the remove operation was successful.
        """
        server_coll = self.db.servers
        res = await server_coll.update_one({"_id": server_id}, {
            '$set': {"bot_in_server": False}})
        if res.acknowledged:
            logger.info(
                f"Marked the bot as not in server {server_id} in {res.modified_count} docs")
        else:
            logger.error(f"Failed to mark the bot as not in server {server_id}")
        return res.acknowledged

    async def add_file(self, message: discord.Message) -> int:
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
        num_docs = await files_coll.count_documents({"message_id": message.id}, limit=1)
        if num_docs:
            return True

        for file in message.attachments:
            # We've already added this file
            n_doc = await files_coll.count_documents({"_id": file.id}, limit=1)
            if n_doc:
                return True
            file_info = utils.attachment_to_mongo_dict(message, file)
            res = await files_coll.insert_one(file_info)
            if res.acknowledged:
                logger.info(
                    f"Inserted new file: {res.inserted_id} with file id: {file.id}")
                files_added += 1
            else:
                logger.error(f"Failed to insert file with _id: {file.id}")
        return files_added

    async def remove_file(self, file_id: str):
        """
        Remove a file.

        Args:
            file: The id of the file to remove

        Returns:
            Whether the file was succesfully removed.
        """
        files_coll = self.db.files
        res = await files_coll.delete_one({"_id": file_id})
        if res.acknowledged:
            logger.info(f"Deleted {res.deleted_count} docs with _id: {file_id}")
        else:
            logger.error(f"Failed to delete file: {file_id}")
        return res.acknowledged

    async def mass_remove_file(self, serv_id: str):
        """
        Remove a file.

        Args:
            serv_id: The id of the server/channel to remove all files from

        Returns:
            Whether the delete operation was succesfully performed and at least 1 file was deleted.
        """
        files_coll = self.db.files
        res = await files_coll.delete_many({"guild_id": serv_id})
        if res.acknowledged:
            logger.info(
                f"Deleted {res.deleted_count} files with guild_id: {serv_id}")
        else:
            logger.error(f"Failed to delete files with guild_id: {serv_id}")
        return res.acknowledged

    async def verify(self, serv_id: int):
        """Verify a server."""
        res = await self.db.servers.find_one(
            {"_id": serv_id},
            {"verified": 1}
        )
        return res["verified"]


async def basic_tests():
    """Run Basic tests."""
    mg = MgClient()
    # await mg.add_file()
    # await mg.add_server()

if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(basic_tests())
