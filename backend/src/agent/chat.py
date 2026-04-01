import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer, util
from src.data.vectordb import VectorDB
from src.data.build_data import update_knowledge
import pickle
from src.config.prompt import PROMPT

# =========================
# DEVICE SETUP
# =========================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# =========================
# LOAD VECTOR DB
# =========================

vectordb = VectorDB()
vectordb.load()

# =========================
# LOAD MODELS
# =========================
# Sentence Transformer for reranking
rank_model = SentenceTransformer("all-MiniLM-L6-v2")

# Chat model
chat_model_name = "gpt2"
chat_tokenizer = AutoTokenizer.from_pretrained(chat_model_name)
chat_model = AutoModelForCausalLM.from_pretrained(chat_model_name).to(device)
chat_model.eval()


# =========================
# HELPER FUNCTIONS
# =========================

def get_similar_queries(query, num=3):
    """Generate multiple query variations using the LLM."""
    results = []
    prompt = f"Rewrite the following query in different ways:\n{query}\n"

    inputs = chat_tokenizer(prompt, return_tensors="pt").to(device)
    outputs = chat_model.generate(
        **inputs,
        max_new_tokens=50,
        do_sample=True,
        temperature=0.9,
        top_p=0.95,
        num_return_sequences=num
    )

    for out in outputs:
        text = chat_tokenizer.decode(out, skip_special_tokens=True)
        results.append(text.replace(prompt, "").strip())

    return list(set(results))

def is_confident(top_docs, threshold=0.4):
    return top_docs and top_docs[0][1] >= threshold

def rag_recall(query, top_k=3):
    """
    1. Retrieve top documents using FAISS (vector DB)
    2. Rerank using sentence transformer embeddings
    """
    # 1️⃣ Retrieve multiple variations
    queries = get_similar_queries(query)
    all_results = []

    for q in queries:
        results = vectordb.search(q, k=5)  # returns (doc, score)
        all_results.extend(results)

    # remove duplicates
    unique_docs = {}
    for doc, score in all_results:
        if doc not in unique_docs:
            unique_docs[doc] = score

    docs = list(unique_docs.keys())

    # 2️⃣ Rerank using sentence embeddings
    if docs:
        embeddings = rank_model.encode([query] + docs, convert_to_tensor=True)
        query_emb = embeddings[0]
        doc_embs = embeddings[1:]
        scores = util.cos_sim(query_emb, doc_embs)[0]
        ranked = sorted(zip(docs, scores.tolist()), key=lambda x: x[1], reverse=True)
    else:
        ranked = []

    return ranked[:top_k]  # return top_k docs


def build_prompt(docs, query):
    context = "\n\n".join([doc for doc, _ in docs])
    prompt = f"""
{PROMPT}

Context:
{context}

Question:
{query}

Answer:
"""
    return prompt


def generate_answer(prompt, max_tokens=150):
    inputs = chat_tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to(device)
    output_ids = chat_model.generate(
        **inputs,
        max_new_tokens=max_tokens,
        do_sample=True,
        temperature=0.7,
        top_p=0.9
    )

    input_len = inputs["input_ids"].shape[1]
    generated_tokens = output_ids[0][input_len:]
    response = chat_tokenizer.decode(generated_tokens, skip_special_tokens=True)
    return response


# =========================
# MAIN LOOP
# =========================
if __name__ == "__main__":
    while True:
        query = input("Ask to know recent news: ").strip()
        if not query:
            continue
        update_knowledge()  
        top_docs = rag_recall(query)
        if not is_confident(top_docs):
            print("\nAnswer:\n I can't provide an answer for this question.")
            continue
        answer = generate_answer(build_prompt(top_docs, query))

        print("\nAnswer:\n", answer)
        print("\nSources:")
        for i, (doc, score) in enumerate(top_docs):
            print(f"{i+1}. (score={round(score,3)}) {doc}")