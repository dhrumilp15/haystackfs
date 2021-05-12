import json
import discord
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConflictError, RequestError
from typing import List, Dict
from datetime import datetime


class ElasticSearchClient():
    def __init__(
            self,
            elastic_domain: str,
            elastic_port: str):
        self.ES = self.make_connection(elastic_domain, elastic_port)

    def make_connection(self, domain: str, port: str) -> Elasticsearch:
        try:
            return Elasticsearch(domain + ':' + port)
        except BaseException as err:
            print(f"Encountered {err}")

    def clear_index(self, index: str):
        try:
            self.ES.indices.delete(index=index, ignore=[400, 404])
        except BaseException as err:
            print(err)

    def create_index(self, index: str):
        if not self.ES.indices.exists(index):
            self.ES.indices.create(
                index=index,
                body=json.load(
                    open('elasticsearchconfig.json', 'r')
                )
            )

    def check_if_doc_exists(self, file: discord.Attachment, index: int):
        return self.ES.exists(index=str(index), id=str(file.id))

    def create_doc(self, message: discord.Message, index: int):
        for file in message.attachments:
            print(f"Attempting to create {file.filename}")
            try:
                body = {
                    "author": str(message.author.id),
                    "author_name": message.author.name,
                    "channel_id": str(message.channel.id),
                    "content": message.content,
                    "created_at":
                    message.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "file_id": str(file.id),
                    "file_name": file.filename,
                    "mimetype": file.content_type,
                    "message_id": str(message.id),
                    "proxy_url": file.proxy_url,
                    "size": str(file.size),
                    "url": file.url,
                }
                if file.height and file.width:
                    body["height"] = str(file.height)
                    body["width"] = str(file.width)
                self.ES.create(index=str(index), id=str(file.id), body=body)
            except ConflictError as err:
                print(err)
                continue

    def delete_doc(self, file_id: int, index: int):
        """Removes a document from the index"""
        if self.ES.exists(index=str(index), id=str(file_id)):
            self.ES.delete(index=str(index), id=str(file_id))

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
    ):
        """Searches for files by their filename

        Args:
            filename: A str of the filename
            index: A str of the index
            filetype: A str of the file's mimetype
            author: A discord.User of the author whose files to search for

        Returns:
            A list of dicts of files
        """
        if not self.ES.indices.exists(str(index)):
            print("Creating a new index since one doesn't exist")
            self.create_index(str(index))
            return
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
        return self.ES.search(index=str(index), body=query)["hits"]["hits"]

    def search_message_id(self, message_id: int, index: int) -> List[Dict]:
        """Searches for files by their message id

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
        return self.ES.search(index=str(index), body=query)["hits"]["hits"]

    def get_all_docs(self, index: int):
        """Get all docs in ES"""
        result = self.ES.search(
            index=str(index),
            body={
                "query": {
                    "match_all": {}
                }
            }
        )
        return result["hits"]["hits"]

    def get_all_indices(self):
        return self.ES.indices.get('*')


if __name__ == '__main__':
    ElasticSearchClient('http://localhost', '9200')
