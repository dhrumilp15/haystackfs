import json
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConflictError, RequestError


class ElasticSearchConnector():
    def __init__(self, elastic_domain: str, elastic_port: str, index: str = 'file_index'):
        self.es = self.make_connection(elastic_domain, elastic_port)
        self.index = index
        self.create_index()

    def make_connection(self, domain: str, port: str):
        try:
            return Elasticsearch(domain + ':' + port)
        except Exception as err:
            print(f"Encountered {err}")
            return None

    def create_index(self):
        try:
            self.es.indices.create(index=self.index, body=json.load(
                open('elasticsearchconfig.json', 'r')))
        except (ConflictError, RequestError):
            print("The index has already been created!")

    def check_if_doc_exists(self, file_name: str):
        return self.es.exists(index=self.index, id=file_name)

    def create_doc(self, file, message):
        if self.check_if_doc_exists(file.filename):
            self.delete_doc(file.filename)
        try:
            body = {
                "author": str(message.author.id),
                "author_name": message.author.name,
                "file_id": str(file.id),
                "file_name": file.filename,
                "created": str(message.created_at),
                "mimetype": str(file.content_type),
                "size": str(file.size),
                "proxy_url": str(file.proxy_url),
                "url": str(file.url)
            }
            if file.height and file.width:
                body["height"] = file.height
                body["width"] = file.width

            self.es.create(index=self.index, id=file.filename, body=body)
            return True
        except ConflictError as err:
            print(f"Error is {err}")
            return False

    def delete_doc(self, file_name):
        """Removes a document from the index"""
        if self.check_if_doc_exists(file_name):
            self.es.delete(index=self.index, id=file_name)

    def search(self, text: str):
        query = {"from": 0, "size": 20, "query": {
            "match": {"file_name": {"query": text, "operator": "and"}}}}
        res = self.es.search(index=self.index, body=query)
        return res["hits"]["hits"]

    def get_all_docs(self):
        """Get all docs in ES"""
        result = self.es.search(
            index=self.index,
            body={
                "query": {
                    "match_all": {}
                }
            }
        )
        print(result["hits"]["hits"])
        return result


if __name__ == '__main__':
    es = ElasticSearchConnector('http://localhost', '9200', 'file_index')
