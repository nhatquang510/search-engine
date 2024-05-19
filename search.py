"""The Search class is use for connecting to Elasticsearch service"""

from elasticsearch import Elasticsearch
import requests
import json

class Search:

    data_source = "https://raw.githubusercontent.com/sfatew/News-Aggregator/main/data/final_articles.json"

    def __init__(self) -> None:
        #connect to the service
        self.es = Elasticsearch('https://4ldowmp64k:au0mi38fmu@beech-758078219.us-east-1.bonsaisearch.net')
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
        r = requests.get(self.data_source)
        documents = r.json()
        ## with open('data.json', 'rt') as f:
        ##     documents = json.loads(f.read())
        return self.insert_documents(index_name=index_name, documents=documents)

    def search(self, index_name, body, size, from_):
        return self.es.search(index=index_name, body=body, size=size, from_=from_)

    def retrieve_document(self, index_name, id):
        return self.es.get(index=index_name, id=id)