from SPARQLWrapper import SPARQLWrapper, JSON
from requests.exceptions import RequestException

def run_sparql_select(endpoint: str, query: str) -> dict:
    try:
        sparql = SPARQLWrapper(endpoint)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        return results
    except RequestException as e:
        raise RuntimeError(f"Could not connect to Fuseki at {endpoint}. Error: {e}")
    except Exception as e:
        raise RuntimeError(f"SPARQL execution error on Fuseki: {e}")