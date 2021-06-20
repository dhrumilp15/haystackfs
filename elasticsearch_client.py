"""The ElasticSearch Client."""
import json
import discord
from elasticsearch import Elasticsearch
import elasticsearch
from elasticsearch.exceptions import ConflictError, ConnectionError
from typing import List, Dict
from datetime import datetime

from config import CONFIG

CONN_ERR = "Could not connect to ElasticSearch. Please report this issue to dhrumilp15#4369 or on the discord server"


class ElasticSearchClient():
    """The ElasticSearch Client."""

    def __init__(self, domain=None, port=None):
        """Initialize the ElasticSearch client."""
        if domain and port:
            self.ES = self.connect(domain, port)
        else:
            self.ES = self.connect(
                CONFIG["ELASTIC_DOMAIN"],
                CONFIG["ELASTIC_PORT"])
        # self.last_snapshot = None
        # snapshot_body = {
        #     "type": "url", "settings": {
        # "url": "http://download.elasticsearch.org/definitiveguide/sigterms_demo/"}}
        # self.ES.snapshot.create_repository(
        #     repository='MAIN', body=snapshot_body)

    def connect(self, domain: str, port: str) -> Elasticsearch:
        """Connect to the ElasticSearch API."""
        try:
            return Elasticsearch(domain + ':' + port)
        except ConnectionError as err:
            print(f"Encountered {err}")

    def clear_index(self, index: str):
        """
        Clear all documents from an index.

        Arguments:
            index: The index to clear
        """
        try:
            self.ES.indices.delete(index=index, ignore=[400, 404])
        except ConnectionError:
            return CONN_ERR

    def create_index(self, index: str):
        """
        Create an index.

        Arguments:
            index: The name of the index to create
        """
        try:
            self.ES.indices.create(
                index=index,
                body=json.load(
                    open('elasticsearchconfig.json', 'r')
                )
            )
        except ConnectionError:
            return CONN_ERR

    def check_if_doc_exists(self, file: discord.Attachment, index: int) -> bool:
        """
        Check whether a doc exists.

        Arguments:
            file: The file to check
            index: The index to search

        Returns:
            Whether the ElasticSearch index has the file
        """
        try:
            res = self.ES.exists(index=str(index), id=str(file.id))
        except ConnectionError:
            return CONN_ERR
        return res

    def create_doc(self, message: discord.Message, index: int):
        """
        Create a document in a given index.

        Arguments:
            message: The message to upload to an index
            index: The index to upload to
        """
        for file in message.attachments:
            print(f"Attempting to create {file.filename}")
            body = {
                "author": str(message.author.id),
                "author_name": message.author.name,
                "channel_id": str(message.channel.id),
                "content": message.content,
                "created_at":
                message.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "file_name": file.filename,
                "mimetype": file.content_type,
                "message_id": str(message.id),
                "size": str(file.size),
                "url": file.url,
            }
            if file.height and file.width:
                body["height"] = str(file.height)
                body["width"] = str(file.width)
            try:
                self.ES.create(index=str(index), id=str(file.id), body=body)
            except (ConflictError, ConnectionError) as err:
                print(err)
                continue

    def make_snapshot(self):
        """Make a snapshot of the ElasticSearch Indices."""
        self.last_snapshot = "snap_" + datetime.strftime(
            datetime.now(), "%Y-%M-%DT%H:%m:%s")
        self.ES.snapshot.create(
            repository='test',
            snapshot=self.last_snapshot,
            wait_for_completion=True,
        )

    def restore_from_snapshot(self):
        """Restore from last snapshot."""
        if not self.last_snapshot:
            return "SNAPSHOT HAS NOT YET BEEN INITIALIZED"

    def delete_doc(self, file_id: int, index: int):
        """
        Remove a document from the index.

        Arguments:
            file_id: The id of the file to delete
            index: The index that contains the file
        """
        try:
            self.ES.delete(index=str(index), id=str(file_id))
        except (ConnectionError, elasticsearch.FileNotFoundError):
            return

    def search(
            self,
            filename: str,
            index: int,
            filetype: str = None,
            author: discord.User = None,
            channel: discord.channel = None,
            content: str = None,
            after: datetime = None,
            before: datetime = None,
    ) -> List[Dict]:
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
        try:
            if not self.ES.indices.exists(str(index)):
                print("Creating a new index since one doesn't exist")
                self.create_index(str(index))
                return
        except ConnectionError:
            return CONN_ERR
        query = {
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
        if filetype is not None:
            query["query"]["bool"]["must"].append(
                {
                    "match": {
                        "mimetype": filetype
                    }
                }
            )
        if author is not None:
            query["query"]["bool"]["must"].append(
                {
                    "term": {
                        "author": str(author.id)
                    }
                }
            )
        if channel is not None:
            query["query"]["bool"]["must"].append(
                {
                    "term": {
                        "channel_id": str(channel.id)
                    }
                }
            )
        if before is not None:
            query["query"]["bool"]["must"].append(
                {
                    "range": {
                        "created_at": {
                            "lt": before
                        }
                    }
                }
            )
        if after is not None:
            query["query"]["bool"]["must"].append(
                {
                    "range": {
                        "created_at": {
                            "gt": after
                        }
                    }
                }
            )
        if content is not None:
            query["query"]["bool"]["must"].append(
                {
                    "match": {
                        "content": {
                            "query": content,
                            "fuzziness": "AUTO"
                        }
                    }
                }
            )

        # if mentions is not None:
        #     query["query"]["nested"] = {"path": "user", "query": {"bool": {
        #         "must": list(map(lambda x: {"match": {"user.id": x.id}}, mentions))}}}
        try:
            res = self.ES.search(index=str(index), body=query)["hits"]["hits"]
        except ConnectionError:
            return CONN_ERR
        return res

    def search_message_id(self, message_id: int, index: int) -> List[Dict]:
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
            res = self.ES.search(index=str(index), body=query)["hits"]["hits"]
        except ConnectionError:
            return CONN_ERR
        return res

    def get_all_docs(self, index: int) -> str or List[Dict]:
        """
        Get all docs in ES.

        Arguments:
            index: The index of the pieces
        """
        try:
            result = self.ES.search(
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

    def get_all_indices(self):
        """Get all indices."""
        try:
            res = self.ES.indices.get('*')
        except ConnectionError:
            return CONN_ERR
        return res


if __name__ == '__main__':
    es = ElasticSearchClient(domain='http://localhost', port='8000')
    print(es.get_all_indices())
    print(es.get_all_docs(0))
    print(es.search_message_id(0, 0))
    print(es.search('bob', 0))
    print(es.create_index(0))
    print(es.clear_index(0))
    # print(es.check_if_doc_exists(discord.Attachment(), 0))
    # print(es.create_doc(discord.Message(state="", channel="", data=""), 0))
