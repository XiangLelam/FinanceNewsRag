import faiss
import pickle
from sentence_transformers import SentenceTransformer
import os

class VectorDB:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.index = None
        self.texts = []

    def build(self, docs):
        # Extract texts
        texts = [doc["text"] for doc in docs]

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

        # 3. Store full docs (not just text)
        self.texts = docs

    def save(self):
        faiss.write_index(self.index, "faiss.index")
        with open("texts.pkl", "wb") as f:
            pickle.dump(self.texts, f)

    def load(self):
        if not os.path.exists("faiss.index") or not os.path.exists("texts.pkl"):
            print("⚠️ No vector DB found")
            self.index = None
            self.texts = []
            return False

        self.index = faiss.read_index("faiss.index")
        with open("texts.pkl", "rb") as f:
            self.texts = pickle.load(f)

        print("✅ Vector DB loaded")
        return True

    def search(self, query, k=10):
        q_vec = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        ).astype("float32")

        D, I = self.index.search(q_vec, k)

        results = []
        for idx, score in zip(I[0], D[0]):
            results.append((self.texts[idx], float(score)))

        return results

            

            

