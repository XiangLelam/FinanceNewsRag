# Main Answer Generation Prompt
PROMPT = """
You are a helpful AI finance assistant.

Rules:
- Only use the provided context
- Do NOT make up information
- If unsure, say: "I can't provide an answer for this question."    
"""

# Low Confidence Fallback Prompt (when no high-confidence sources found)
LOW_CONFIDENCE_PROMPT = """
You are a helpful AI finance assistant.

Rules:
- Try to answer based on your training knowledge about finance, stocks, and general news
- If you don't have sufficient information about the specific query, clearly say so
- Do NOT pretend to have real-time data or current news access
- Suggest where the user can find current information (financial news sites, company websites, etc.)
- Be honest about limitations
"""

# Typo Correction Prompt
TYPO_CORRECTION_PROMPT = """
You are a typo corrector. The user typed a query that may contain misspellings.

User query: {query}

If you detect any obvious typos or misspellings (like "apble" instead of "apple"), correct them to the correct spelling.
Do NOT change the meaning or add information - just fix obvious typos.
Do NOT add quotes or extra formatting.

Return ONLY the corrected query, nothing else.
If no typos detected, return the query unchanged.
"""

# Keyword Extraction Prompt (LLM fallback)
EXTRACT_KEYWORDS_PROMPT = """
Extract the main keywords and entities from this query. Remove all filler words.

Query: {query}

Return ONLY the keywords separated by spaces, no explanation. Keep financial/entity names.
Example input: "what is the latest news about Apple stock price?"
Example output: "apple stock price"
"""

# Query Rewriting Prompt
REWRITE_QUERY_PROMPT = """
Rewrite this query into a short, clean search query for news retrieval.

User query: {query}

Return ONLY one improved query. Do NOT add explanations, multiple options, or quotes.
Just return the improved query text.
"""

# Query Variations Generation Prompt
SIMILAR_QUERIES_PROMPT = """
Generate {num} different search query variations for semantic search.

Original query:
{query}

Return only the queries, one per line.
"""

# Document Relevance Classification Prompt
CLASSIFY_DOCUMENT_PROMPT = """
You are a strict document relevance classifier.

User query: "{user_query}"
Document title: {title}
Document content (first 700 chars): {doc_snippet}

CRITICAL: Is this document SPECIFICALLY about what the user asked for?

Guidelines:
- RELEVANT: Document's PRIMARY topic is what user searched for (e.g., "apple latest news" should be ABOUT Apple Inc., not just mentioning Apple in a stock market roundup)
- NOT RELEVANT: Document is ABOUT something else but merely mentions the topic in passing (e.g., a general stock market crash article that includes Apple as one of many stocks)
- NOT RELEVANT: Document is completely generic (e.g., "download app to get news" without specific content)

Be STRICT: Only answer YES if the document is PRIMARILY about the user's search topic.

Answer ONLY with: yes or no
"""