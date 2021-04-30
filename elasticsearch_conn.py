import json
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConflictError


class ElasticSearchConnector():
    def __init__(self, elastic_domain: str, elastic_port: str, index: str):
        self.es = self.make_connection(elastic_domain, elastic_port)
        self.index = index
        self.create_index()

    def make_connection(self, domain: str, port: str):
        try:
            es = Elasticsearch(domain + ':' + port)
            print(json.dumps(Elasticsearch.info(es), indent=4))
            return es
        except Exception as err:
            print(f"Encountered {err}")
            return None

    def create_index(self):
        if not self.es.indices.exists(index=self.index):
            self.es.indices.create(index=self.index, body=json.load(
                open('elasticsearchconfig.json', 'r')))

    def check_if_doc_exists(self, file_name: str):
        return self.es.exists(index=self.index, id=file_name)

    def create_doc(self, file_id, file_name, created, ts, mimetype, filetype, uid, size):
        try:
            # filename, file_extension = os.path.splitext(file_name)
            body = {
                "file_id": file_id, "file_name": file_name, "created": str(created), "timestamp": str(ts), "mimetype": mimetype, "filetype": filetype, "user_id": uid, "size": str(size),
            }
            self.es.create(index=self.index, id=file_name, body=body)
            return True
        except ConflictError as err:
            print(f"Error is {err}")
            return False

    def delete_doc(self, file_name):
        """Removes a document from the index"""
        if(self.check_if_doc_exists(file_name)):
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
        # print(result["hits"]["hits"])
        return result


if __name__ == '__main__':
    es = ElasticSearchConnector('http://localhost', '9200', 'file_index')
