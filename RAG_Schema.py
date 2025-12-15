import rdflib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class SchemaRAG:
    def __init__(self, ttl_path: str):
        # Load RDF graph from Turtle file
        self.graph = rdflib.Graph()
        self.graph.parse(ttl_path, format="turtle")

        # Build schema entries
        self.entries = self._build_entries()
        if not self.entries:
            raise ValueError("No schema entries found in TTL file.")

        # Build TF‑IDF vectorizer on schema entries
        self.vectorizer = TfidfVectorizer(analyzer="word", ngram_range=(1, 2))
        self.embeddings = self.vectorizer.fit_transform(self.entries)

    def _curie(self, uri):
        """Normalize URI to CURIE form if possible."""
        try:
            return self.graph.namespace_manager.normalizeUri(uri)
        except Exception:
            return str(uri)

    def _build_entries(self):
        """Extract schema entries from RDF graph."""
        entries = []

        # Classes
        for s in self.graph.subjects(rdflib.RDF.type, rdflib.OWL.Class):
            entries.append(f"Class {self._curie(s)}")

        # Object properties
        for s in self.graph.subjects(rdflib.RDF.type, rdflib.OWL.ObjectProperty):
            domain = next(self.graph.objects(s, rdflib.RDFS.domain), None)
            range_ = next(self.graph.objects(s, rdflib.RDFS.range), None)
            entries.append(
                f"ObjectProperty {self._curie(s)} domain {self._curie(domain) if domain else 'unknown'} "
                f"range {self._curie(range_) if range_ else 'unknown'}"
            )

        # Datatype properties
        for s in self.graph.subjects(rdflib.RDF.type, rdflib.OWL.DatatypeProperty):
            domain = next(self.graph.objects(s, rdflib.RDFS.domain), None)
            range_ = next(self.graph.objects(s, rdflib.RDFS.range), None)
            entries.append(
                f"DatatypeProperty {self._curie(s)} domain {self._curie(domain) if domain else 'unknown'} "
                f"range {self._curie(range_) if range_ else 'unknown'}"
            )

        # Common hints for idShort/value/description
        for s in self.graph.subjects(None, None):
            for p in self.graph.predicates(s, None):
                p_curie = self._curie(p)
                if p_curie.endswith(("idShort", "value", "description")):
                    entries.append(f"Predicate {p_curie} often used with properties (idShort/value/description).")

        return entries

    def retrieve(self, question: str, k: int = 20):
        """Retrieve top‑k schema entries relevant to the question."""
        if not question.strip():
            return ""

        # Transform question into TF‑IDF vector
        q_vec = self.vectorizer.transform([question])

        # Compute cosine similarity
        scores = cosine_similarity(self.embeddings, q_vec).ravel()

        # Get top‑k indices
        top_idx = scores.argsort()[::-1][:k]

        return "\n".join(self.entries[i] for i in top_idx)
