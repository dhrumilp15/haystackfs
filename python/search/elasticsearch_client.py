"""The ElasticSearch Client."""
import json
from .async_search_client import AsyncSearchClient
import discord
import elasticsearch
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ConflictError, ConnectionError
from typing import List, Dict
from datetime import datetime
from utils import attachment_to_search_dict

from config import CONFIG

CONN_ERR = "Could not connect to ElasticSearch. Please report this issue to dhrumilp15#4369 or on the discord server"


class ElasticSearchClient(AsyncSearchClient):
    """The ElasticSearch Client."""

    def __init__(self, domain=None, port=None):
        """Initialize the ElasticSearch client."""
        if domain and port:
            self.ES = self.connect(domain, port)
        else:
            self.ES = self.connect(
                CONFIG.ELASTIC_DOMAIN,
                CONFIG.ELASTIC_PORT)

    def connect(self, domain: str, port: str) -> AsyncElasticsearch:
        """Connect to the ElasticSearch API."""
        try:
            return AsyncElasticsearch(domain + ':' + port)
        except ConnectionError:
            return CONN_ERR

    def initialize(self, *args, **kwargs):
        """Initialize client."""
        pass

    async def clear_index(self, index: str):
        """
        Clear all documents from an index.

        Arguments:
            index: The index to clear
        """
        try:
            await self.ES.indices.delete(index=index, ignore=[400, 404])
        except ConnectionError:
            return CONN_ERR

    async def create_index(self, index: str):
        """
        Create an index.

        Arguments:
            index: The name of the index to create
        """
        try:
            await self.ES.indices.create(
                index=index,
                body=json.load(
                    open('elasticsearchconfig.json', 'r')
                ),
                ignore=[400]
            )
        except ConnectionError:
            return CONN_ERR

    async def create_doc(self, message: discord.Message, index: int):
        """
        Create a document in a given index.

        Arguments:
            message: The message to upload to an index
            index: The index to upload to
        """
        for file in message.attachments:
            body = attachment_to_search_dict(message, file)
            try:
                res = await self.ES.create(index=str(index), id=str(file.id), body=body)
            except (ConflictError, ConnectionError) as err:
                continue

    async def make_snapshot(self):
        """Make a snapshot of the ElasticSearch Indices."""
        self.last_snapshot = "snap_" + datetime.strftime(
            datetime.now(), "%Y-%M-%DT%H:%m:%s")
        res = await self.ES.snapshot.create(
            repository='test',
            snapshot=self.last_snapshot,
            wait_for_completion=True,
        )

    def restore_from_snapshot(self):
        """Restore from last snapshot."""
        if not self.last_snapshot:
            return "SNAPSHOT HAS NOT YET BEEN INITIALIZED"

    async def delete_doc(self, file_id: int, index: int):
        """
        Remove a document from the index.

        Arguments:
            file_id: The id of the file to delete
            index: The index that contains the file
        """
        try:
            await self.ES.delete(index=str(index), id=str(file_id))
        except (ConnectionError, elasticsearch.NotFoundError):
            return CONN_ERR

    async def search(self, filename: str, index: int, **kwargs) -> List[Dict] or str:
        """
        Search for files.

        Args:
            filename: A str of the filename
            index: A str of the index
            filetype: A str of the file's mimetype
            author: A discord.User of the author whose files to search for

        Returns:
            A list of dicts of files
        """
        index_res = await self.create_index(str(index))
        if index_res:
            return index_res
        query = {
            # "_source": False,
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "file_name": {
                                    "query": filename,
                                    "fuzziness": "AUTO",
                                }
                            }
                        }
                    ]
                }
            }
        }
        if kwargs.get("mimetype"):
            query["query"]["bool"]["must"].append(
                {
                    "match": {
                        "mimetype": kwargs["mimetype"]
                    }
                }
            )
        if kwargs.get("author"):
            query["query"]["bool"]["must"].append(
                {
                    "term": {
                        "author": str(kwargs["author"].id)
                    }
                }
            )
        if kwargs.get("channel"):
            query["query"]["bool"]["must"].append(
                {
                    "term": {
                        "channel_id": str(kwargs["channel"].id)
                    }
                }
            )
        if kwargs.get("before"):
            query["query"]["bool"]["must"].append(
                {
                    "range": {
                        "created_at": {
                            "lt": kwargs["before"]
                        }
                    }
                }
            )
        if kwargs.get("after"):
            query["query"]["bool"]["must"].append(
                {
                    "range": {
                        "created_at": {
                            "gt": kwargs["after"]
                        }
                    }
                }
            )
        if kwargs.get("content"):
            query["query"]["bool"]["must"].append(
                {
                    "match": {
                        "content": {
                            "query": kwargs["content"],
                            "fuzziness": "AUTO"
                        }
                    }
                }
            )
        # if mentions is not None:
        #     query["query"]["nested"] = {"path": "user", "query": {"bool": {
        #         "must": list(map(lambda x: {"match": {"user.id": x.id}}, mentions))}}}
        try:
            res = await self.ES.search(index=str(index), body=query)
        except ConnectionError:
            return CONN_ERR
        return res["hits"]["hits"]

    async def search_message_id(self, message_id: int, index: int) -> List[Dict]:
        """
        Search for files by message id.

        Args:
            message_id: An int of the message id
            index: A str of the index

        Returns:
            A list of dicts of files
        """
        query = {
            "query": {
                "match": {
                    "message_id": {
                        "query": str(message_id),
                    }
                }
            }
        }
        try:
            res = await self.ES.search(index=str(index), body=query)
        except ConnectionError:
            return CONN_ERR
        return res["hits"]["hits"]

    async def get_all_docs(self, index: int) -> str or List[Dict]:
        """
        Get all docs in ES.

        Arguments:
            index: The index of the pieces
        """
        try:
            result = await self.ES.search(
                index=str(index),
                body={
                    "query": {
                        "match_all": {}
                    }
                }
            )
        except ConnectionError:
            return CONN_ERR
        return result["hits"]["hits"]

    async def get_all_indices(self):
        """Get all indices."""
        try:
            res = await self.ES.indices.get('*')
        except ConnectionError:
            return CONN_ERR
        return res

    async def close(self):
        """Close the AsyncElasticSearch object."""
        res = await self.ES.close()
        return res


async def basic_tests():
    """Run Basic tests."""
    es = ElasticSearchClient()
    await es.get_all_indices()
    await es.create_index(0)
    await es.clear_index(0)
    await es.close()

if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(basic_tests())
    # loop.close()
    # print(es.check_if_doc_exists(discord.Attachment(), 0))
    # print(es.create_doc(discord.Message(state="", channel="", data=""), 0))
