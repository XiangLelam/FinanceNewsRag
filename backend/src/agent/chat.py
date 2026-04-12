import torch
from sentence_transformers import SentenceTransformer, util
from src.data.vectordb import VectorDB
from src.data.knowledge_process import KnowledgeProcessing
from src.config.prompt import PROMPT
import ollama


client = ollama.Client(host='http://host.docker.internal:11434')
# =========================
# DEVICE SETUP
# =========================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# =========================
# LOAD MODELS
# =========================
# Sentence Transformer for reranking
rank_model = SentenceTransformer("all-MiniLM-L6-v2")


# =========================
# HELPER FUNCTIONS
# =========================

def get_similar_queries(query, num=3):
    prompt = f"""
Generate {num} different search query variations for semantic search.

Original query:
{query}

Return only the queries, one per line.
"""

    response = client.chat(
        model="mistral",
        messages=[{"role": "user", "content": prompt}]
    )

    text = response["message"]["content"]

    queries = text.split("\n")
    queries = [q.strip("-• ") for q in queries if q.strip()]

    return list(set(queries))[:num]

def is_confident(top_docs, threshold=0.4):
    return top_docs and top_docs[0][1] >= threshold

def rag_recall(query, top_k=3):
    """
    1. Retrieve top documents using FAISS (vector DB)
    2. Rerank using sentence transformer embeddings
    """
    # 🔥 ALWAYS rebuild knowledge for each query
    print("🔄 Building knowledge base for query...")

    kp = KnowledgeProcessing(query)
    kp.update_knowledge()

    # 🔥 Load the newly built DB
    vectordb = VectorDB()
    vectordb.load()
    
    # 1️⃣ Retrieve multiple variations
    queries = get_similar_queries(query)
    all_results = []

    for q in queries:
        results = vectordb.search(q, k=5)  # returns (doc, score)
        all_results.extend(results)

    # remove duplicates by text content
    unique_docs = {}
    for doc, score in all_results:
        # Handle both dict and string formats
        text_key = doc["text"] if isinstance(doc, dict) else str(doc)
        if text_key not in unique_docs:
            unique_docs[text_key] = (doc, score)

    # Extract docs with their scores
    docs_with_scores = list(unique_docs.values())
    docs = [doc for doc, score in docs_with_scores]

    # 2️⃣ Rerank using sentence embeddings
    if docs:
        query_emb = rank_model.encode(query, convert_to_tensor=True)
        # Extract text for encoding
        doc_texts = [doc["text"] if isinstance(doc, dict) else doc for doc in docs]
        doc_embs = rank_model.encode(doc_texts, convert_to_tensor=True)
        scores = util.cos_sim(query_emb, doc_embs)[0]
        ranked = sorted(zip(docs, scores.tolist()), key=lambda x: x[1], reverse=True)
    else:
        ranked = []

    return ranked[:top_k]  # return top_k docs


def build_prompt(docs, query):
    # Extract text content from docs (handle both dict and string)
    context_parts = []
    for doc, _ in docs:
        if isinstance(doc, dict):
            context_parts.append(doc["text"])
        else:
            context_parts.append(str(doc))
    context = "\n\n".join(context_parts)
    prompt = f"""
{PROMPT}

Context:
{context}

Question:
{query}

Answer:
"""
    return prompt

def generate_answer(prompt):
    try:

        response = client.chat(
            model="mistral",
            messages=[{"role": "user", "content": prompt}]
        )

        return response["message"]["content"]

    except Exception as e:
        print("ERROR:", str(e))   # 👈 THIS WILL SHOW REAL PROBLEM
        return "Internal error occurred"