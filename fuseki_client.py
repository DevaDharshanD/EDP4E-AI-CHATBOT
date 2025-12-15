# fuseki_client.py

from SPARQLWrapper import SPARQLWrapper, JSON
from requests.exceptions import RequestException

# CHANGE: The return type is now 'dict' to reflect the standard SPARQL JSON output
def run_sparql_select(endpoint: str, query: str) -> dict:
    """
    Executes a SPARQL SELECT query against the Jena Fuseki endpoint.
    Returns the full standard SPARQL JSON result dictionary.
    """
    try:
        sparql = SPARQLWrapper(endpoint)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        
        # Execute the query and convert to a Python dictionary
        # This dictionary already has the structure {"head": {...}, "results": {"bindings": [...]}}
        results = sparql.query().convert()
        
        # CRITICAL FIX: Return the full, standard dictionary structure.
        # This structure matches what the client-side JavaScript expects 
        # for accessing data.results.results.bindings.
        return results

    except RequestException as e:
        # Catch connection issues (e.g., Fuseki is down)
        raise RuntimeError(f"Could not connect to Fuseki at {endpoint}. Error: {e}")
    except Exception as e:
        # Catch SPARQL syntax or execution errors reported by Fuseki
        # In a real app, you might want to log the full error from the Fuseki response here
        raise RuntimeError(f"SPARQL execution error on Fuseki: {e}")