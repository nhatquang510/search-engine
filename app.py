from flask import Flask, render_template, request, Response, jsonify
from search import Search
import re
import json
from urllib.parse import unquote, quote


app = Flask(__name__)
es = Search()


@app.get('/TagsList') #for java client take date
def TagsList(size = 800, from_ = 0):
    search_results, aggs = search(query='', size=size, from_=from_)
    results = []
    for agg in aggs:
        result = [agg]
        for key, count in aggs[agg].items():
            result.append({key: count})
        results.append(result)

    json_file = json.dumps(results, indent=4)
    return Response(json_file, status=200, mimetype='application/json')


@app.get('/search/<size>/<from_>') #for java client take data
def java_search_all(size, from_):
    search_results, aggs = search(query='', size=size, from_=from_)
    results = []
    total=search_results['hits']['total']['value']
    results.append(total)
    for document in search_results['hits']['hits']:
        article = document['_source']
        d = {}
        d['id'] = article['id']
        d['titles'] = article['title']
        d['score'] = document['_score']
        results.append(d)
        
    json_file = json.dumps(results, indent=4)
    return Response(json_file, status=200, mimetype='application/json')


@app.get('/search=<encoded_query>/<size>/<from_>') #for java client take data
def java_search(encoded_query, size, from_):
    query = unquote(encoded_query)
    search_results, aggs = search(query=query, size=size, from_=from_)
    results = []
    total=search_results['hits']['total']['value']
    results.append(total)
    for document in search_results['hits']['hits']:
        article = document['_source']
        d = {}
        d['id'] = article['id']
        d['titles'] = article['title']
        d['score'] = document['_score']
        results.append(d)
        
    json_file = json.dumps(results, indent=4)
    return Response(json_file, status=200, mimetype='application/json')

## if data type change, only need to modify extract_filters, search and get_document

@app.route('/')
def index():
    return render_template('index.html', data_source = es.data_source)

@app.route('/', methods=['POST'])
def handle_search():
    query = request.form.get('query', '')
    size = 5
    from_ = request.form.get('from_', type=int, default=0)
    
    results, aggs = search(query=query, size=size, from_=from_)

    return render_template('index.html', datasource = es.data_source, results=results['hits']['hits'],
                           query=query, size = size, from_=from_,
                           total=results['hits']['total']['value'], aggs = aggs)
    
@app.route('/reloadDataFromJava', methods=['GET'])
def reloadDataFromJava():
    """Regenerate the Elasticsearch index."""
    response = es.reindex("my_documents")
    reindex_status = 'Index with '+ str(len(response["items"])) + ' documents created in ' + str(response["took"]) + ' milliseconds.'
    return reindex_status

@app.route('/reindex', methods=['GET'])
def reindex():
    """Regenerate the Elasticsearch index."""
    response = es.reindex("my_documents")
    reindex_status = 'Index with '+ str(len(response["items"])) + ' documents created in ' + str(response["took"]) + ' milliseconds.'
    return render_template('dataloading.html', reindex_status = reindex_status)

@app.get("/document/<id>")
def get_document(id):
    document = es.retrieve_document("my_documents", id)
    title = document["_source"]["title"]
    paragraphs = document["_source"]["detailed_content"].split("\n")
    url = document["_source"]["article_link"]
    return render_template("document.html", title=title, paragraphs=paragraphs, url=url)

def extract_filters(query):
    filters = []

    # tags filter
    while(True):
        filter_regex = r"tags:([^\s]+)\s*"
        m = re.search(filter_regex, query)
        if m:
            filters.append(
                {
                    "term": {"tags.keyword": {"value": m.group(1)}},
                }
            )
            query = re.sub(filter_regex, "", query, 1).strip()
        else:
            break

    # website_source filter
    while(True):
        filter_regex = r"website_source:([^\s]+)\s*"
        m = re.search(filter_regex, query)
        if m:
            filters.append(
                {
                    "term": {"website_source.keyword": {"value": m.group(1)}},
                }
            )
            query = re.sub(filter_regex, "", query, 1).strip()
        else:
            break

    return {"filter": filters}, query


def search(query, size, from_):
    filters, parsed_query = extract_filters(query)
    
    if parsed_query:
        search_query = {
            'must': {
                'multi_match': {
                    'query': parsed_query,
                    'fields': ['title', 'summary', 'detailed_content'],
                }
            }
        }
    else:
        search_query = {
            'must': {
                'match_all': {}
            }
        }

    results = es.search("my_documents",
        body=
        {
            "query":
            {
                'bool': {
                    **search_query,
                    **filters
                }
            },
            "aggs":
            {
                'tags-agg': {
                    'terms': {
                        'field': 'tags.keyword',
                    }
                },
                'website_source-agg': {
                    'terms': {
                        'field': 'website_source.keyword',
                    }
                },
            }
        },
        size=size,
        from_=from_
    )
    aggs = {
        'Tags': {
            bucket['key']: bucket['doc_count']
            for bucket in results['aggregations']['tags-agg']['buckets']
        },
        'Website source': {
            bucket['key']: bucket['doc_count']
            for bucket in results['aggregations']['website_source-agg']['buckets']
        },
    }
    return results, aggs


if __name__ == '__main__':
    app.run(debug=True)