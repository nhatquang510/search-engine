from flask import Flask, render_template, request
from search import Search
import re

app = Flask(__name__)
es = Search()

## if data type change, only need to modify handle_search and get_document

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/', methods=['POST'])
def handle_search():
    query = request.form.get('query', '')
    filters, parsed_query = extract_filters(query)
    size = 5
    from_ = request.form.get('from_', type=int, default=0)
    
    if parsed_query:
        search_query = {
            'must': {
                'multi_match': {
                    'query': parsed_query,
                    'fields': ['name', 'summary', 'content'],
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
                'year-agg': {
                    'date_histogram': {
                        'field': 'updated_at',
                        'calendar_interval': 'year',
                        'format': 'yyyy',
                    },
                },
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
        'Year': {
            bucket['key_as_string']: bucket['doc_count']
            for bucket in results['aggregations']['year-agg']['buckets']
            if bucket['doc_count'] > 0
        },
    }
    return render_template('index.html', results=results['hits']['hits'],
                           query=query, size = size, from_=from_,
                           total=results['hits']['total']['value'], aggs = aggs)
    
@app.route('/reindex', methods=['POST'])
def reindex():
    """Regenerate the Elasticsearch index."""
    response = es.reindex("my_documents")
    reindex_status = 'Index with '+ str(len(response["items"])) + ' documents created in ' + str(response["took"]) + ' milliseconds.'
    return render_template('dataloading.html', reindex_status = reindex_status)

@app.get("/document/<id>")
def get_document(id):
    document = es.retrieve_document("my_documents", id)
    title = document["_source"]["name"]
    paragraphs = document["_source"]["content"].split("\n")
    return render_template("document.html", title=title, paragraphs=paragraphs)

def extract_filters(query):
    filters = []

    filter_regex = r"category:([^\s]+)\s*"
    m = re.search(filter_regex, query)
    if m:
        filters.append(
            {
                "term": {"category.keyword": {"value": m.group(1)}},
            }
        )
        query = re.sub(filter_regex, "", query).strip()

    filter_regex = r"year:([^\s]+)\s*"
    m = re.search(filter_regex, query)
    if m:
        filters.append(
            {
                "range": {
                    "updated_at": {
                        "gte": f"{m.group(1)}||/y",
                        "lte": f"{m.group(1)}||/y",
                    }
                },
            }
        )
        query = re.sub(filter_regex, "", query).strip()

    return {"filter": filters}, query


if __name__ == '__main__':
    app.run(debug=True)