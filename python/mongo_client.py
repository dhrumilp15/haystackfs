"""MongoDB Client."""
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import discord
from typing import List, Dict
import json

from config import CONFIG
import utils
import os
from bson import json_util
# import utils.server_to_mongo_dict as server_to_mongo_dict
# import utils.attachment_to_mongo_dict as attachment_to_mongo_dict
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
fh = logging.FileHandler('mongodb.log', encoding='utf-8', mode='w')
fh.setFormatter(formatter)
logger.addHandler(fh)


class MgClient:
    """MongoDB Client."""

    def __init__(self, mongo_endpoint: str = None, db_name: str = None):
        """Initialize the MongoDB Client and database."""
        self.client, self.db = None, None
        try:
            if mongo_endpoint and db_name:
                self.client = AsyncIOMotorClient(mongo_endpoint)
                self.db = self.client[db_name]
                logger.info(f"Connected to MongoDB! Current database: {self.db.name}")
        except:
            logger.info("Couldn't connect to MongoDB")

    async def get_file(self, file_id: int) -> dict:
        """
        Get the file url of the file id.

        Args:
            file_id: The id of the file to retrieve.

        Returns:
            The file url as a str.
        """
        if not self.db:
            return dict()
        res = await self.db.files.find_one({"_id": int(file_id)}, {"url": 1, "file_name": 1})
        return res

    async def log_command(self, command, *args, **kwargs) -> bool:
        if not self.db:
            return False
        ctx = args[0]
        command_type = 'search'
        if 'delete' in command.__name__:
            command_type = 'delete'
        if 'remove' in command.__name__:
            command_type = 'remove'
        for key, val in kwargs.items():
            kwargs[key] = repr(val)
        command_info = utils.command_to_mongo_dict(command_type, ctx, kwargs)
        command_coll = self.db.commands
        res = await command_coll.insert_one(command_info)
        if res.acknowledged:
            logger.info(f"Inserted new command: {res.inserted_id}")
        else:
            logger.error(f"Failed to insert new command {ctx.id}")
        return res.acknowledged

    async def add_server(self, server: discord.Guild or discord.DMChannel) -> bool:
        """
        Add a server or channel to the `servers` collection.

        Args:
            server: The server or DMChannel to add to the collection

        Returns:
            Whether the insert operation was successful
        """
        if not self.db:
            return False
        server_coll = self.db.servers
        # We've already added the server
        num_docs = await server_coll.count_documents({"_id": server.id}, limit=1)
        if num_docs:
            return True
        server_info = utils.server_to_mongo_dict(server)
        res = await server_coll.insert_one(server_info)
        if res.acknowledged:
            logger.info(f"Inserted new server: {res.inserted_id} with server id: {server.id}")
        else:
            logger.error(f"Failed to insert new server with server _id: {server.id}")
        return res.acknowledged

    async def remove_server(self, server_id: int) -> bool:
        """
        Mark the bot as not in this server.

        Args:
            guild: The guild to remove the bot from.

        Returns:
            Whether the remove operation was successful.
        """
        if not self.db:
            return False
        server_coll = self.db.servers
        res = await server_coll.update_one({"_id": server_id}, {'$set': {"bot_in_server": False}})
        if res.acknowledged:
            logger.info(f"Marked the bot as not in server {server_id} in {res.modified_count} docs")
        else:
            logger.error(f"Failed to mark the bot as not in server {server_id}")
        return res.acknowledged

    async def remove_server_docs(self, server_id: int) -> bool:
        """
        Remove any docs from a server.

        Args:
            guild: The guild to remove docs from.

        Returns:
            Whether the remove operation was successful.
        """
        if not self.db:
            return False
        files_coll = self.db.files
        res = await files_coll.delete_many({"guild_id": server_id})
        return res.acknowledged

    async def add_file(self, message: discord.Message) -> int:
        """
        Add a file to the `files` collection.

        Args:
            message: The discord.Message containing the files.

        Returns:
            The number of files in the message successfully inserted into the collection
        """
        if not self.db:
            return 0
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
                continue
            file_info = utils.attachment_to_mongo_dict(message, file)
            res = await files_coll.insert_one(file_info)
            if res.acknowledged:
                logger.info(f"Inserted new file: {res.inserted_id} with file id: {file.id}")
                files_added += 1
            else:
                logger.error(f"Failed to insert file with _id: {file.id}")
        return files_added

    async def remove_file(self, file_ids: List[str]) -> bool:
        """
        Remove files.

        Args:
            file_ids: A list of file ids to remove.

        Returns:
            Whether the file was succesfully removed.
        """
        if not self.db:
            return False
        files_coll = self.db.files
        res = await files_coll.delete_many({"_id": {"$in": file_ids}})
        return res.acknowledged

    async def dump_snapshot(self, collection):
        """
        Dump a snapshot of a collection to local fs as a json. We choose json because of its portability.

        Args:
            collection: A collection from mongodb.
        """
        if not self.db:
            return
        path = f"{CONFIG.DB_NAME}_{collection.name}"
        if not os.path.exists(path):
            os.mkdir(path)
        coll = {collection.name: [file async for file in collection.find()]}
        print(f'Snapshot of {CONFIG.DB_NAME}/{collection.name} at {datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}')
        with open(f"{path}/snapshot_" + datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + ".json", 'w') as f:
            json.dump(coll, fp=f, default=json_util.default, indent=4)

    async def load_from_snapshot(self, snapshot_path: str) -> bool:
        """
        Load the database from the json snapshot.

        Args:
            snapshot_path: The path to the snapshot.json

        Returns:
            Whether the operation was completed successfully.
        """
        if not self.db:
            return False
        ack = False
        with open(snapshot_path, 'r') as f:
            docs = json.load(f, object_hook=json_util.object_hook)
            res = await self.db.files.insert_many(docs['files'])
            ack = res.acknowledged
        return ack

    async def mass_remove_file(self, serv_id: str) -> bool:
        """
        Remove a file.

        Args:
            serv_id: The id of the server/channel to remove all files from

        Returns:
            Whether the delete operation was succesfully performed and at least 1 file was deleted.
        """
        if not self.db:
            return False
        files_coll = self.db.files
        res = await files_coll.delete_many({"guild_id": serv_id})
        if res.acknowledged:
            logger.info(f"Deleted {res.deleted_count} files with guild_id: {serv_id}")
        else:
            logger.error(f"Failed to delete files with guild_id: {serv_id}")
        return res.acknowledged

    async def verify(self, serv_id: int) -> bool:
        """Verify a server."""
        if not self.db:
            return False
        res = await self.db.servers.find_one({"_id": serv_id}, {"verified": 1})
        return res["verified"]

    async def delete_files_from_inactive_servers(self) -> bool:
        """
        Delete files that belong to servers that the bot is in.

        Returns:
            Whether the delete operation was acknowledged.
        """
        if not self.db:
            return False
        server_coll = self.db.servers
        inactive_servers = server_coll.find({"bot_in_server": False})
        inactive_serv = [serv['_id'] async for serv in inactive_servers]
        files_coll = self.db.files
        await self.dump_snapshot(files_coll)

        n_docs = await files_coll.count_documents({})
        res = await files_coll.delete_many({"guild_id": {"$in": inactive_serv}})
        if res.acknowledged:
            logger.info(f"Deleted {res.deleted_count} files")
        else:
            logger.error(f"Failed to delete files")
        return res.acknowledged, res.deleted_count != n_docs


async def basic_tests():
    """Run Basic tests."""
    mg = MgClient()
    # await mg.add_file()
    # await mg.add_server()

if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(basic_tests())
