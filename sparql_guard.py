import re

def validate_sparql(query: str):
    if not query:
        raise ValueError("Query is empty.")
    
    query_start = query.strip().upper()

    if not query_start.startswith("PREFIX") and not query_start.startswith("SELECT"):
         raise ValueError("Only SPARQL SELECT queries are allowed.")

    forbidden_keywords = ["UPDATE", "DELETE", "INSERT", "SERVICE", "LOAD", "CLEAR", "DROP"]
    for keyword in forbidden_keywords:
        if re.search(r'\b' + keyword + r'\b', query, re.IGNORECASE):
            raise ValueError(f"Forbidden keyword '{keyword}' found in query.")

    if "SELECT" in query_start and "WHERE" not in query_start:
        raise ValueError("SPARQL SELECT query is missing a WHERE clause.")