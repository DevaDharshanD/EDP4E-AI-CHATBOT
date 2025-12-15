import re

def stable_prefix_block() -> str:
    """Returns the standardized prefix block for SPARQL queries."""
    # Ensure these prefixes match the URIs in your schema.ttl
    return """
@prefix:<http://edp4e.org#> .
@prefix bp: <http://edp4e.org#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
"""

def validate_sparql(query: str):
    """
    Performs basic validation on the generated SPARQL query for security and format.
    Raises an error if validation fails.
    """
    if not query:
        raise ValueError("Query is empty.")
    
    # Check if the query starts with PREFIX (allowing multi-line prefixes) or SELECT
    query_start = query.strip().upper()

    # Security Check 1: Only allow SELECT (allows PREFIX blocks before SELECT)
    if not query_start.startswith("PREFIX") and not query_start.startswith("SELECT"):
         raise ValueError("Only SPARQL SELECT queries are allowed (no UPDATE, INSERT, or DELETE).")

    # Security Check 2: Disallow dangerous keywords (case-insensitive search after prefix stripping)
    forbidden_keywords = ["UPDATE", "DELETE", "INSERT", "SERVICE", "LOAD", "CLEAR", "DROP"]
    for keyword in forbidden_keywords:
        if re.search(r'\b' + keyword + r'\b', query, re.IGNORECASE):
            raise ValueError(f"Forbidden keyword '{keyword}' found in query.")

    # Basic Format Check: Ensure WHERE clause exists for SELECT
    if "SELECT" in query_start and "WHERE" not in query_start:
        raise ValueError("SPARQL SELECT query is missing a WHERE clause.")