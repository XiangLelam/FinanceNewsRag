import faiss
import pickle
from sentence_transformers import SentenceTransformer
import os
import src.config.constant as cons

_embedding_model = None


def get_embedding_model():
    """Load the embedding model once and share it (VectorDB is created per request)."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(cons.EMBEDDING_MODEL)
    return _embedding_model


class VectorDB:
    def __init__(self):
        self.model = get_embedding_model()
        self.index = None
        self.texts = []

    def is_initialized(self):
        """Check if the vector DB index is ready to search."""
        return self.index is not None and len(self.texts) > 0

    def build(self, docs):
        # Extract texts
        texts = [f"{doc.get('title') or ''}\n{doc['text']}" for doc in docs]

        # 1. Generate embeddings
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).astype("float32")

        # 2. Build FAISS index
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)

        # 3. Store full docs
        self.texts = docs
        print(f"Vector DB built with {len(docs)} documents")

    def save(self):
        if not self.is_initialized():
            print("Cannot save empty vector DB")
            return

        faiss.write_index(self.index, "faiss.index")
        with open("texts.pkl", "wb") as f:
            pickle.dump({"model": cons.EMBEDDING_MODEL, "docs": self.texts}, f)
        print(f"Vector DB saved ({len(self.texts)} docs)")

    def load(self):
        if not os.path.exists("faiss.index") or not os.path.exists("texts.pkl"):
            print("No vector DB found on disk")
            self.index = None
            self.texts = []
            return False

        with open("texts.pkl", "rb") as f:
            data = pickle.load(f)

        if not isinstance(data, dict) or data.get("model") != cons.EMBEDDING_MODEL:
            print("Vector DB on disk was built with a different embedding model - ignoring it")
            self.index = None
            self.texts = []
            return False

        self.index = faiss.read_index("faiss.index")
        self.texts = data["docs"]

        print(f"Vector DB loaded ({len(self.texts)} docs)")
        return True

    def search(self, query, k=10):
        """Search the vector DB. Returns empty list if index not initialized."""
        if self.index is None:
            print("Vector DB index not initialized. Returning empty results.")
            return []

        q_vec = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        ).astype("float32")

        D, I = self.index.search(q_vec, k)

        results = []
        for idx, score in zip(I[0], D[0]):
            if idx < 0:
                continue
            results.append((self.texts[idx], float(score)))

        return results
