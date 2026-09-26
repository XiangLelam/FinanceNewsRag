import os
import re
from dotenv import load_dotenv
import ollama
from src.config.prompt import (
    TYPO_CORRECTION_PROMPT,
    EXTRACT_KEYWORDS_PROMPT,
    REWRITE_QUERY_PROMPT,
    SIMILAR_QUERIES_PROMPT,
    CLASSIFY_DOCUMENT_PROMPT
)

load_dotenv()

OLLAMA_HOST = os.getenv('OLLAMA_HOST')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'mistral')

client = ollama.Client(host=OLLAMA_HOST)


def typo_corrector_agent(query):
    try:
        correction_prompt = TYPO_CORRECTION_PROMPT.format(query=query)
        
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": correction_prompt}],
            stream=False
        )
        
        corrected = response["message"]["content"].strip().split('\n')[0].strip().strip('"').strip()
        corrected = re.sub(r'\s*\([^)]*\)\s*$', '', corrected).strip()

        if not corrected or len(corrected) > len(query) + 10:
            return query

        if corrected != query:
            print(f"Typo correction: '{query}' → '{corrected}'")
        
        return corrected
            
    except Exception as e:
        print(f"Typo correction error: {e}, using original query")
        return query


def extract_keywords_agent_llm(query):
    try:
        prompt = EXTRACT_KEYWORDS_PROMPT.format(query=query)
        
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        
        keywords = response["message"]["content"].strip().split('\n')[0].replace('"', '').strip()
        print(f"LLM extracted keywords: {keywords}")
        return keywords
    
    except Exception as e:
        print(f"LLM keyword extraction failed: {e}")
        return query


def rewrite_query_agent(query, history_text=""):
    try:
        prompt = REWRITE_QUERY_PROMPT.format(
            query=query,
            history=history_text or "(no previous messages)"
        )

        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )

        rewritten = response["message"]["content"].strip().strip('"').strip()
        rewritten = rewritten.split('\n')[0].strip()
        return rewritten or query
    except Exception as e:
        print(f"Query rewrite failed, using original: {e}")
        return query


def get_similar_queries_agent(query, num=3):
    try:
        prompt = SIMILAR_QUERIES_PROMPT.format(query=query, num=num)

        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response["message"]["content"]

        queries = text.split("\n")
        queries = [re.sub(r'^\s*(?:[-*•]|\d+[.)])\s*', '', q).strip().strip('"').strip() for q in queries]
        queries = [q for q in queries if q]

        return list(set(queries))[:num]
    except Exception as e:
        print(f"Query variation generation failed: {e}")
        return []


def classify_document_relevance_agent(doc, user_query):
    try:
        doc_text = (doc.get("text", "") + " " + doc.get("title", "")).lower()
        doc_snippet = doc_text[:700]
        title = doc.get("title", "No title").strip()
        
        classification_prompt = CLASSIFY_DOCUMENT_PROMPT.format(
            user_query=user_query,
            title=title,
            doc_snippet=doc_snippet
        )
        
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": classification_prompt}],
            stream=False
        )
        
        result = response["message"]["content"].strip().lower()
        
        if result.strip('"\'.! ').startswith("yes"):
            return "relevant"
        else:
            return "not_relevant"
            
    except Exception as e:
        print(f"Classification error: {e}, accepting document")
        return "relevant"


def generate_answer_agent(prompt):
    """Generate answer using LLM with given prompt."""
    try:
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )

        return response["message"]["content"]

    except Exception as e:
        print("ERROR:", str(e))
        return "Internal error occurred"
