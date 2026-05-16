from sentence_transformers import SentenceTransformer, util
from src.data.vectordb import VectorDB
from src.config.prompt import PROMPT
from src.agent.agents import (
    typo_corrector_agent,
    extract_keywords_agent_llm,
    get_similar_queries_agent,
    classify_document_relevance_agent,
)
from datetime import datetime
import src.config.constant as cons


rank_model = SentenceTransformer("all-MiniLM-L6-v2")

CURRENT_KB_KEYWORDS = None
STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
    'by', 'from', 'about', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have',
    'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
    'might', 'can', 'must', 'shall', 'as', 'if', 'than', 'that', 'this', 'which',
    'who', 'what', 'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both',
    'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
    'same', 'so', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
    'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'would', 'like',
    'want', 'know', 'see', 'get', 'latest', 'new', 'today', 'today\'s', 'want', 'news', 'article'
}

def extract_keywords(query):

    try:
        print(f"Raw query: '{query}'")
        corrected = typo_corrector_agent(query)
        if corrected != query:
            print(f"Typo corrected: '{query}' → '{corrected}'")
        
        # 2. Extract words, remove stopwords and special characters
        words = corrected.lower().split()
        words = [w.strip('"').strip("'").strip() for w in words]
        filtered_words = [w for w in words if w not in STOPWORDS and len(w) > 2 and w]
        
        print(f"Words after stopword removal: {filtered_words}")
        
        if filtered_words:
            keywords = " ".join(filtered_words)
            print(f"Extracted keywords: '{keywords}'")
            return keywords
        
        # 3. If filtering removes everything, try LLM extraction
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
    
    # For small documents, accept if they exist
    if len(doc_text) < cons.MIN_DOCUMENT_TEXT_LENGTH:
        return True
    
    # Use LLM to classify based on FULL query context
    relevance = classify_document_relevance_agent(doc, query)
    
    if relevance == "relevant":
        print(f"Document relevant to query")
        return True
    else:
        print(f"Document not relevant to query")
        return False

def should_update_kb(current_keywords):

    global CURRENT_KB_KEYWORDS
    
    # If no KB keywords tracked yet, update
    if CURRENT_KB_KEYWORDS is None:
        return True
    
    # If keywords are identical, skip update (KB is fresh)
    if CURRENT_KB_KEYWORDS == current_keywords:
        print("KB already contains latest articles for these keywords, skipping update")
        return False
    
    # Different keywords = need to update
    return True


def mark_kb_updated(keywords):
    """Mark KB as updated with these keywords."""
    global CURRENT_KB_KEYWORDS
    CURRENT_KB_KEYWORDS = keywords
    print(f"KB marked as updated for keywords: '{keywords}'")


def rag_recall(query, normalized_query=None, top_k=3, skip_kb_update=False):

    vectordb = VectorDB()
    vectordb.load()
    
    if not vectordb.is_initialized():
        print("Vector DB not initialized or empty - returning empty results")
        print(f"Index: {vectordb.index}")
        print(f"Texts loaded: {len(vectordb.texts) if vectordb.texts else 0}")
        return []

    # Check if we should skip KB update based on keywords
    if not skip_kb_update:

        # Extract keywords to check KB persistence
        temp_keywords = extract_keywords(query)
        if not should_update_kb(temp_keywords):
            skip_kb_update = True 
        else:
            mark_kb_updated(temp_keywords)

    queries = [query]

    if normalized_query and normalized_query != query:
        queries.append(normalized_query)

    # Add LLM-generated variations (based on normalized query if available)
    base_query = normalized_query if normalized_query else query
    variations = get_similar_queries_agent(base_query)

    queries.extend(variations)

    # Remove duplicates
    queries = list(set(queries))

    print(f"\nRAG Retrieval Pipeline:")
    print(f"Original query: '{query}'")
    print(f"Normalized query: '{normalized_query}'")
    print(f"Query variations: {queries}")

    # Retrieve from FAISS
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

        # Keep highest score if exact duplicate
        if text_key not in unique_docs or unique_docs[text_key][1] < score:
            unique_docs[text_key] = (doc, score)

    docs_with_scores = list(unique_docs.values())
    docs = [doc for doc, _ in docs_with_scores]
    
    # Entity validation: filter out generic news that doesn't mention the query entity
    print(f"\nEntity validation: checking if docs contain keywords from '{query}'")
    validated_docs = []
    for doc, score in docs_with_scores:
        if validate_entity_match(doc, query, min_keywords=1):
            validated_docs.append((doc, score))
    
    if not validated_docs:
        print(f"No documents passed entity validation (too generic)")
        return []
    
    docs = [doc for doc, _ in validated_docs]
    print(f"Passed entity validation: {len(docs)}/{len(docs_with_scores)} docs")
    if docs:
        # Use normalized query for better semantic matching
        rank_query = normalized_query if normalized_query else query
        query_emb = rank_model.encode(rank_query, convert_to_tensor=True)

        doc_texts = [
            doc["text"] if isinstance(doc, dict) else doc
            for doc in docs
        ]

        doc_embs = rank_model.encode(doc_texts, convert_to_tensor=True)

        scores = util.cos_sim(query_emb, doc_embs)[0].tolist()

        now = datetime.now()
        ranked = []
        
        for doc, score in zip(docs, scores):
            # Apply temporal boost if date is available
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

        # Sort by final score
        ranked = sorted(ranked, key=lambda x: x[1], reverse=True)
        
        print(f"Top 3 scores: {[f'{score:.4f}' for _, score in ranked[:3]]}")
        
        #Semantic deduplication - remove highly similar docs
        filtered_ranked = []
        seen_docs = []
        
        for doc, score in ranked:
            is_duplicate = False
            doc_text = doc["text"] if isinstance(doc, dict) else str(doc)
            doc_emb = rank_model.encode(doc_text, convert_to_tensor=True)
            
            for seen_doc_emb in seen_docs:
                similarity = util.cos_sim(doc_emb, seen_doc_emb)[0].item()
                # If similarity exceeds threshold, treat as duplicate/near-duplicate
                if similarity > cons.SEMANTIC_DUPLICATE_THRESHOLD:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered_ranked.append((doc, score))
                seen_docs.append(doc_emb)
        
        ranked = filtered_ranked
        
        # URL-based deduplication - ensure each source appears only once
        url_dedup = {}
        for doc, score in ranked:
            url = doc.get("url", "N/A") if isinstance(doc, dict) else "N/A"
            if url not in url_dedup or url_dedup[url][1] < score:
                url_dedup[url] = (doc, score)
        
        ranked = list(url_dedup.values())
        print(f" After URL deduplication: {len(ranked)} unique sources")
    else:
        ranked = []

    return ranked[:top_k]


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