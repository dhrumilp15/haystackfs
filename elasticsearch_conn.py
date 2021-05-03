import json
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConflictError


class ElasticSearchConnector():
    def __init__(self, elastic_domain: str, elastic_port: str, index: str = 'file_index'):
        self.ES = self.make_connection(elastic_domain, elastic_port)
        self.index = index
        self.create_index()

    def make_connection(self, domain: str, port: str):
        try:
            return Elasticsearch(domain + ':' + port)
        except Exception as err:
            print(f"Encountered {err}")
            return None

    def create_index(self):
        self.ES.indices.delete(index=self.index, ignore=[400, 404])
        self.ES.indices.create(index=self.index, body=json.load(
            open('elasticsearchconfig.json', 'r')))

    def check_if_doc_exists(self, filename):
        return self.ES.exists(index=self.index, id=filename)

    def create_doc(self, message):
        for file in message.attachments:
            print("Attempting to create {}, hash: {}".format(
                file.filename, hash(file)))

            try:
                # filename = self.update_duplicate_filename(file.filename)
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
                self.ES.create(index=self.index, id=file.id, body=body)
                return True
            except ConflictError as err:
                print(f"Error is {err}")
                return False

    def delete_doc(self, filename):
        """Removes a document from the index"""
        if self.check_if_doc_exists(filename):
            self.ES.delete(index=self.index, id=filename)

    def update_duplicate_filename(self, filename):
        existing_filenames = self.search(filename)
        if not existing_filenames:
            return filename

        prev_word = existing_filenames[-1]['_source']['file_name']
        for idx, char in enumerate(prev_word[::-1]):
            if char == '_':
                version = int(prev_word[-idx + 1:])
                filename += '_' + str(version + 1)
                return filename
            if char == '.':
                break

        return filename + '_1'

    def search(self, filename: str):
        query = {
            "query": {
                "match": {
                    "file_name": {
                        "query": filename,
                        "fuzziness": "AUTO",
                    }
                }
            }
        }
        return self.ES.search(index=self.index, body=query)["hits"]["hits"]

    def get_all_docs(self):
        """Get all docs in ES"""
        result = self.ES.search(
            index=self.index,
            body={
                "query": {
                    "match_all": {}
                }
            }
        )
        return result["hits"]["hits"]


if __name__ == '__main__':
    ElasticSearchConnector('http://localhost', '9200', 'file_index')
