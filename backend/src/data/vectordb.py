from openai import OpenAI
import numpy as np
import faiss
import tqdm
from src.data.datatabase import load_all_data,connect_db
import json
import pickle
from sentence_transformers import SentenceTransformer

class VectorDB:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.index = None
        self.texts = []

    def build(self, chunks):
        # 1. Generate embeddings
        embeddings = self.model.encode(chunks, convert_to_numpy=True, normalize_embeddings=True)
        print(embeddings.shape)
        vectors = embeddings.astype("float32")  # FAISS requires float32
    
        # 2. Build FAISS index
        dim = vectors.shape[1]
        self.index = faiss.IndexFlatIP(dim)  # Inner product similarity
        self.index.add(vectors)

        # 3. Store texts
        self.texts = chunks

    def save(self):
        faiss.write_index(self.index, "faiss.index")
        with open("texts.pkl", "wb") as f:
            pickle.dump(self.texts, f)

    def load(self):
        self.index = faiss.read_index("faiss.index")
        with open("texts.pkl", "rb") as f:
            self.texts = pickle.load(f)

    def search(self, query, k=10):
        # Encode query
        q_vec = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        ).astype("float32")

        # FAISS search
        D, I = self.index.search(q_vec, k)

        results = []
        for idx, score in zip(I[0], D[0]):
            results.append((self.texts[idx], float(score)))

        return results
            

            

