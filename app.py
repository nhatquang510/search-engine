from flask import Flask, render_template, request, Response
from search import Search
import re
import json
from urllib.parse import unquote


app = Flask(__name__)
es = Search()

@app.get('/search/<size>/<from_>') #for java client take date
def java_search_all(size, from_):
    search_results, aggs = search(query='', size=size, from_=from_)
    results = []
    for document in search_results['hits']['hits']:
        article = document['_source']
        d = {}
        d['id'] = document['_id']
        d['titles'] = article['title']
        results.append(d)
        
    json_file = json.dumps(results, indent=4)
    return Response(json_file, status=200, mimetype='application/json')


@app.get('/search=<encoded_query>/<size>/<from_>') #for java client take date
def java_search(encoded_query, size, from_):
    query = unquote(encoded_query)
    results, aggs = search(query=query, size=size, from_=from_)
    json_file = json.dumps(results['hits']['hits'], indent=4)
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

    # category filter
    while(True):
        filter_regex = r"category:([^\s]+)\s*"
        m = re.search(filter_regex, query)
        if m:
            filters.append(
                {
                    "term": {"category.keyword": {"value": m.group(1)}},
                }
            )
            query = re.sub(filter_regex, "", query, 1).strip()
        else:
            break

    # filter_regex = r"year:([^\s]+)\s*"
    # m = re.search(filter_regex, query)
    # if m:
    #     filters.append(
    #         {
    #             "range": {
    #                 "updated_at": {
    #                     "gte": f"{m.group(1)}||/y",
    #                     "lte": f"{m.group(1)}||/y",
    #                 }
    #             },
    #         }
    #     )
    #     query = re.sub(filter_regex, "", query).strip()

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
                'category-agg': {
                    'terms': {
                        'field': 'category.keyword',
                    }
                },
                # 'year-agg': {
                #     'date_histogram': {
                #         'field': 'updated_at',
                #         'calendar_interval': 'year',
                #         'format': 'yyyy',
                #     },
                # },
            }
        },
        size=size,
        from_=from_
    )
    aggs = {
        'Category': {
            bucket['key']: bucket['doc_count']
            for bucket in results['aggregations']['category-agg']['buckets']
        },
        # 'Year': {
        #     bucket['key_as_string']: bucket['doc_count']
        #     for bucket in results['aggregations']['year-agg']['buckets']
        #     if bucket['doc_count'] > 0
        # },
    }
    return results, aggs


if __name__ == '__main__':
    app.run(debug=True)