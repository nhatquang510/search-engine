"""The Search class is use for connecting to Elasticsearch service"""

from elasticsearch import Elasticsearch
import requests
import json

class Search:

    def __init__(self) -> None:
        #connect to the service
        self.es = Elasticsearch('https://n25v1lruze:3npiimenvf@spruce-256317558.us-east-1.bonsaisearch.net/')
        print(self.es.info())
    
    def create_index(self, name):
        self.es.indices.delete(index=name, ignore_unavailable=True)
        self.es.indices.create(index=name)

    def insert_document(self, index_name, document):
        return self.es.index(index=index_name, body=document)
    
    def insert_documents(self, index_name, documents):
        operations = []
        for document in documents:
            operations.append({"index": {"_index": index_name}})
            operations.append(document)
        return self.es.bulk(body=operations)
    
    def delete_document(self, index_name, id):
        return self.es.delete(index=index_name, id=id)
    
    def reindex(self, index_name):
        self.create_index(index_name)
        r = requests.get('https://raw.githubusercontent.com/nhatquang510/datasets/main/data.json')
        documents = r.json()
        # with open('data.json', 'rt') as f:
        #     documents = json.loads(f.read())
        return self.insert_documents(index_name=index_name, documents=documents)

    def search(self, index_name, body, size, from_):
        return self.es.search(index=index_name, body=body, size=size, from_=from_)

    def retrieve_document(self, index_name, id):
        return self.es.get(index=index_name, id=id)