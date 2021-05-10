import json
import discord
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConflictError, RequestError
from typing import List, Dict


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

    def check_if_doc_exists(self, file: discord.Attachment, index: str):
        return self.ES.exists(index=index, id=file.id)

    def create_doc(self, message: discord.Message, index: str):
        for file in message.attachments:
            print(f"Attempting to create {file.filename}")
            try:
                body = {
                    "author": str(message.author.id),
                    "author_name": message.author.name,
                    "channel_id": str(message.channel.id),
                    "created": str(message.created_at),
                    "file_id": str(file.id),
                    "file_name": file.filename,
                    "mimetype": str(file.content_type),
                    "message_id": str(message.id),
                    "size": str(file.size),
                    "proxy_url": str(file.proxy_url),
                    "url": str(file.url),
                }
                if file.height and file.width:
                    body["height"] = file.height
                    body["width"] = file.width

                self.ES.create(index=index, id=file.id, body=body)
            except ConflictError as err:
                print(err)
                continue

    def delete_doc(self, file_id: str, index: str):
        """Removes a document from the index"""
        if self.ES.exists(index=index, id=file_id):
            self.ES.delete(index=index, id=file_id)

    def search(
            self,
            filename: str,
            index: str,
            filetype: str = None,
            author: str = None):
        """Searches for files by their filename

        Args:
            filename: A str of the filename
            index: A str of the index

        Returns:
            A list of dicts of files
        """
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
                    "match": {
                        "author": author
                    }
                }
            )
        return self.ES.search(index=index, body=query)["hits"]["hits"]

    def search_message_id(self, message_id: int, index: int) -> List[Dict]:
        """Searches for files by their message id

        Args:
            message_id: An int of the message id
            index: A str of the index

        Returns:
            A list of dicts of files
        """
        message_id = str(message_id)
        index = str(index)
        query = {
            "query": {
                "match": {
                    "message_id": {
                        "query": message_id,
                    }
                }
            }
        }
        return self.ES.search(index=index, body=query)["hits"]["hits"]

    def get_all_docs(self, index: str):
        """Get all docs in ES"""
        index = str(index)
        result = self.ES.search(
            index=index,
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
