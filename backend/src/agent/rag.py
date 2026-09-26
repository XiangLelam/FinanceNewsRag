import torch
from sentence_transformers import CrossEncoder, util
from src.data.vectordb import VectorDB, get_embedding_model
from src.agent.agents import (
    typo_corrector_agent,
    extract_keywords_agent_llm,
    get_similar_queries_agent,
    classify_document_relevance_agent,
)
from datetime import datetime
import src.config.constant as cons


rerank_model = CrossEncoder(cons.RERANK_MODEL)

CURRENT_KB_KEYWORDS = None
STOPWORDS = {
    # Articles, conjunctions, prepositions
    'the', 'a', 'an', 'and', 'or', 'but', 'nor', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
    'by', 'from', 'about', 'into', 'as', 'if', 'than', 'so',
    # Auxiliary / modal verbs
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'am', 'have', 'has', 'had',
    'do', 'does', 'did', 'doing', 'will', 'would', 'could', 'should', 'may', 'might',
    'can', 'must', 'shall',
    # Question words and contractions
    'what', 'when', 'where', 'why', 'how', 'who', 'which', 'that', 'this', 'there', 'here',
    "what's", 'whats', "how's", "it's", "there's", "i'm", 'im', "let's", 'lets',
    # Pronouns ("it" is almost always a pronoun in questions, e.g. "is it going up?")
    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'them',
    'my', 'your', 'his', 'its', 'our', 'their',
    # Quantifiers / filler
    'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'any',
    'no', 'not', 'only', 'same', 'just', 'also', 'very', 'much', 'please',
    # Request verbs
    'like', 'want', 'know', 'see', 'get', 'got', 'tell', 'show', 'give', 'find', 'check',
    'look', 'looking', 'need', 'think', 'say', 'said', 'let', 'go', 'going', 'happen',
    'happened', 'happening',
    # News/time filler - the search is already limited to recent articles
    'latest', 'recent', 'recently', 'current', 'currently', 'now', 'today', "today's",
    'yesterday', 'week', 'weeks', 'news', 'article', 'articles', 'update', 'updates',
    'info', 'information', 'details',
}

def extract_keywords(query, correct_typos=True):

    try:
        print(f"Raw query: '{query}'")
        corrected = typo_corrector_agent(query) if correct_typos else query
        if corrected != query:
            print(f"Typo corrected: '{query}' → '{corrected}'")
        
        words = corrected.lower().replace("’", "'").split()
        words = [w.strip('"\'?!.,:;()').strip() for w in words]
        filtered_words = [w for w in words if w not in STOPWORDS and len(w) >= 2]
        
        print(f"Words after stopword removal: {filtered_words}")
        
        if filtered_words:
            keywords = " ".join(filtered_words)
            print(f"Extracted keywords: '{keywords}'")
            return keywords
        
        print("Stopword filtering removed all words, using LLM extraction...")
        return extract_keywords_agent_llm(corrected)
    
    except Exception as e:
        print(f"Keyword extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return query


def is_confident(top_docs, threshold=None):
    if threshold is None:
        threshold = cons.CONFIDENCE_THRESHOLD

    if not top_docs:
        return False
    
    top_score = top_docs[0][1]
    is_confident_result = top_score >= threshold
    print(f"Top document score: {top_score:.4f} (threshold: {threshold}) → {'CONFIDENT (QUALITY MATCH)' if is_confident_result else 'LOW CONFIDENCE (WEAK MATCH)'}")
    return is_confident_result

def validate_entity_match(doc, query, min_keywords=1):
   
    if not isinstance(doc, dict) or not doc.get("text"):
        return True
    
    doc_text = (doc.get("text", "") + " " + doc.get("title", "")).lower()
    
    if len(doc_text) < cons.MIN_DOCUMENT_TEXT_LENGTH:
        return True
    
    relevance = classify_document_relevance_agent(doc, query)
    
    if relevance == "relevant":
        print(f"Document relevant to query")
        return True
    else:
        print(f"Document not relevant to query")
        return False

def should_update_kb(current_keywords):

    global CURRENT_KB_KEYWORDS
    
    if CURRENT_KB_KEYWORDS is None:
        return True
    
    if CURRENT_KB_KEYWORDS == current_keywords:
        print("KB already contains latest articles for these keywords, skipping update")
        return False
    
    return True


def mark_kb_updated(keywords):
    global CURRENT_KB_KEYWORDS
    CURRENT_KB_KEYWORDS = keywords
    print(f"KB marked as updated for keywords: '{keywords}'")


def rag_recall(query, normalized_query=None, keywords=None, top_k=3, skip_kb_update=False):

    vectordb = VectorDB()
    vectordb.load()
    
    if not vectordb.is_initialized():
        print("Vector DB not initialized or empty - returning empty results")
        print(f"Index: {vectordb.index}")
        print(f"Texts loaded: {len(vectordb.texts) if vectordb.texts else 0}")
        return []

    if not skip_kb_update:
        temp_keywords = extract_keywords(query)
        if not should_update_kb(temp_keywords):
            skip_kb_update = True 
        else:
            mark_kb_updated(temp_keywords)

    queries = [query]

    if normalized_query and normalized_query != query:
        queries.append(normalized_query)

    base_query = normalized_query if normalized_query else query
    variations = get_similar_queries_agent(base_query)

    queries.extend(variations)

    queries = list(set(queries))

    print(f"\nRAG Retrieval Pipeline:")
    print(f"Original query: '{query}'")
    print(f"Normalized query: '{normalized_query}'")
    print(f"Query variations: {queries}")

    all_results = []

    for q in queries:
        results = vectordb.search(q, k=cons.SEMANTIC_SEARCH_K)
        if results:
            print(f"Query '{q}' → {len(results)} results (scores: {[f'{s:.3f}' for _, s in results[:3]]})")
        else:
            print(f"Query '{q}' → No results found")
        all_results.extend(results)
    
    if not all_results:
        print("No documents found across all query variations!")
        return []

    unique_docs = {}

    for doc, score in all_results:
        text_key = doc["text"] if isinstance(doc, dict) else str(doc)

        if text_key not in unique_docs or unique_docs[text_key][1] < score:
            unique_docs[text_key] = (doc, score)

    docs_with_scores = list(unique_docs.values())
    docs = [doc for doc, _ in docs_with_scores]
    
    validation_query = normalized_query or query
    print(f"\nEntity validation: checking if docs are relevant to '{validation_query}'")
    validated_docs = []
    for doc, score in docs_with_scores:
        if validate_entity_match(doc, validation_query, min_keywords=1):
            validated_docs.append((doc, score))
    
    if not validated_docs:
        print(f"No documents passed entity validation (too generic)")
        return []
    
    docs = [doc for doc, _ in validated_docs]
    print(f"Passed entity validation: {len(docs)}/{len(docs_with_scores)} docs")
    if docs:
        rank_queries = list({q for q in (query, normalized_query, keywords) if q})
        doc_texts = [
            f"{doc.get('title') or ''}\n{doc['text']}" if isinstance(doc, dict) else doc
            for doc in docs
        ]

        pairs = [(q, text) for q in rank_queries for text in doc_texts]
        pair_scores = rerank_model.predict(pairs, activation_fn=torch.nn.Sigmoid()).tolist()

        n = len(doc_texts)
        scores = [
            max(pair_scores[qi * n + di] for qi in range(len(rank_queries)))
            for di in range(n)
        ]

        now = datetime.now()
        ranked = []

        for doc, score in zip(docs, scores):
            if isinstance(doc, dict) and doc.get("date"):
                try:
                    doc_date = doc["date"]
                    if isinstance(doc_date, str):
                        doc_date = datetime.strptime(doc_date, "%Y-%m-%d %H:%M:%S")
                    
                    days_old = (now - doc_date).days
                    
                    # Recency bonus: more recent = higher score
                    # Formula: 1 / (1 + RECENCY_DECAY_FACTOR * days_old)
                    # Day 0: boost = 1.0, Day 10: boost = 0.5, Day 100: boost = 0.09
                    recency_boost = 1.0 / (1.0 + cons.RECENCY_DECAY_FACTOR * max(days_old, 0))
                    
                    # Apply recency weight and relevance weight
                    final_score = (cons.RELEVANCE_WEIGHT * score) + (cons.RECENCY_WEIGHT * recency_boost)
                except Exception as e:
                    print(f"Temporal weighting error: {e}")
                    final_score = score
            else:
                final_score = score
            
            ranked.append((doc, final_score))

        ranked = sorted(ranked, key=lambda x: x[1], reverse=True)
        
        print(f"Top 3 scores: {[f'{score:.4f}' for _, score in ranked[:3]]}")
        
        filtered_ranked = []
        seen_docs = []
        ranked_embs = get_embedding_model().encode(
            [doc["text"] if isinstance(doc, dict) else str(doc) for doc, _ in ranked],
            convert_to_tensor=True
        )

        for (doc, score), doc_emb in zip(ranked, ranked_embs):
            is_duplicate = False

            for seen_doc_emb in seen_docs:
                similarity = util.cos_sim(doc_emb, seen_doc_emb)[0].item()
                if similarity > cons.SEMANTIC_DUPLICATE_THRESHOLD:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered_ranked.append((doc, score))
                seen_docs.append(doc_emb)
        
        ranked = filtered_ranked
        
        url_dedup = {}
        for doc, score in ranked:
            url = doc.get("url", "N/A") if isinstance(doc, dict) else "N/A"
            if url not in url_dedup or url_dedup[url][1] < score:
                url_dedup[url] = (doc, score)
        
        ranked = list(url_dedup.values())
        print(f" After URL deduplication: {len(ranked)} unique sources")

        confident_ranked = [(doc, score) for doc, score in ranked if score >= cons.CONFIDENCE_THRESHOLD]
        print(f"Above confidence threshold: {len(confident_ranked)}/{len(ranked)} docs")
        if confident_ranked:
            ranked = confident_ranked
    else:
        ranked = []

    return ranked[:top_k]
