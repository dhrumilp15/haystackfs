"""MongoDB Client."""
import dataclasses
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import discord
from typing import List, Tuple
import json

from ..config import CONFIG
from models import Command
import os
from bson import json_util
import traceback

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
        if mongo_endpoint is not None and db_name is not None:
            self.client = AsyncIOMotorClient(mongo_endpoint)
            self.db = self.client[db_name]
            logger.info(f"Connected to MongoDB! Current database: {self.db.name}")

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
        res = await self.db.files.find_one({"_id": int(file_id)}, {"url": 1, "filename": 1})
        return res

    async def log_command(self, command, *args, **kwargs) -> bool:
        """
        Log commands to the database.

        Args:
            command: The user command
            args: Arbitrary arguments, usually context
            kwargs: Query parameters

        Returns:
            Whether the log operation was successful
        """
        try:
            if self.db is None:
                print("db is empty!!")
                return False
            print("Received Log request!!", end=" ")
            print(command.__name__)
            ctx = args[0]
            command_type = 'search'
            if 'delete' in command.__name__:
                command_type = 'delete'
            if 'remove' in command.__name__:
                command_type = 'remove'
            for key, val in kwargs.items():
                kwargs[key] = repr(val)

            command_info = Command.from_discord_interaction(command_type, ctx, kwargs)
            command_coll = self.db.commands
            res = await command_coll.insert_one(dataclasses.asdict(command_info))
            if res.acknowledged:
                logger.info(f"Inserted new command: {res.inserted_id}")
            else:
                logger.error(f"Failed to insert new command {ctx.id}")
            return res.acknowledged
        except:
            traceback.print_exc()
            return False

    async def clear_message_content(self) -> bool:
        """
        Clear message content for files that have been stored for more than 30 days. We use a buffer of 1 day.

        Returns:
            Whether the update operation was successful.
        """
        if not self.db:
            return False
        files_coll = self.db.files
        current_time = datetime.now() - timedelta(days=29)
        await files_coll.update_many({"timestamp": {"$lt": current_time}},
                                     {"$set": {"content": "REMOVED AFTER 30 DAYS"}})

    async def remove_server(self, server_id: int) -> bool:
        """
        Mark the bot as not in this server.

        Args:
            server_id: The guild to remove the bot from.

        Returns:
            Whether the remove operation was successful.
        """
        if not self.db:
            return False
        server_coll = self.db.servers
        try:
            res = await server_coll.update_one({"_id": server_id}, {'$set': {"bot_in_server": False}})
            if res.acknowledged:
                logger.info(f"Marked the bot as not in server {server_id} in {res.modified_count} docs")
            else:
                logger.error(f"Failed to mark the bot as not in server {server_id}")
            return res.acknowledged
        except:
            return False

    async def remove_server_docs(self, server_id: int) -> bool:
        """
        Remove any docs from a server.

        Args:
            server_id: The guild to remove docs from.

        Returns:
            Whether the remove operation was successful.
        """
        if not self.db:
            return False
        files_coll = self.db.files
        try:
            res = await files_coll.delete_many({"guild_id": server_id})
            return res.acknowledged
        except:
            return False

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
        try:
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
        except:
            return 0

    async def remove_file(self, ids: List[str], field: str = "_id") -> bool:
        """
        Remove files.

        Args:
            ids: A list of ids to remove.
            field: The type of id to remove.

        Returns:
            Whether the file was succesfully removed.
        """
        if not self.db:
            return False
        files_coll = self.db.files
        try:
            res = await files_coll.delete_many({field: {"$in": ids}})
            return res.acknowledged
        except:
            return False

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
        try:
            with open(snapshot_path, 'r') as f:
                docs = json.load(f, object_hook=json_util.object_hook)
                res = await self.db.files.insert_many(docs['files'])
                ack = res.acknowledged
        except:
            pass
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
        try:
            res = await files_coll.delete_many({"guild_id": serv_id})
            if res.acknowledged:
                logger.info(f"Deleted {res.deleted_count} files with guild_id: {serv_id}")
            else:
                logger.error(f"Failed to delete files with guild_id: {serv_id}")
            return res.acknowledged
        except:
            return False

    async def delete_files_from_inactive_servers(self) -> Tuple[bool, bool]:
        """
        Delete files that belong to servers that the bot is in.

        Returns:
            Whether the delete operation was acknowledged.
        """
        if not self.db:
            return False
        server_coll = self.db.servers
        try:
            inactive_servers = server_coll.find({"bot_in_server": False})
            inactive_serv = [serv['_id'] async for serv in inactive_servers]
            files_coll = self.db.files

            n_docs = await files_coll.count_documents({})
            res = await files_coll.delete_many({"guild_id": {"$in": inactive_serv}})
            if res.acknowledged:
                logger.info(f"Deleted {res.deleted_count} files")
            else:
                logger.error(f"Failed to delete files")
            return res.acknowledged, res.deleted_count != n_docs
        except:
            return False, False

