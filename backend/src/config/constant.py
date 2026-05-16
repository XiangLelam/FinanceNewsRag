# HTTP & API Configuration
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
REQUEST_TIMEOUT = 10

# GDELT Data Ingestion
GDELT_MAX_RESULTS = 5
GDELT_FALLBACK_QUERY = "stock market news"
MIN_KEYWORD_LENGTH = 3
ARTICLE_SNIPPET_LENGTH = 1000

# Text Processing & Chunking
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# RAG Scoring & Retrieval
CONFIDENCE_THRESHOLD = 0.30
SEMANTIC_SEARCH_K = 5
SEMANTIC_DUPLICATE_THRESHOLD = 0.85
MIN_DOCUMENT_TEXT_LENGTH = 150

# Formula: 1 / (1 + RECENCY_DECAY_FACTOR * days_old)
# Day 0: boost = 1.0, Day 10: boost = 0.5, Day 100: boost = 0.09
RECENCY_DECAY_FACTOR = 0.1
RELEVANCE_WEIGHT = 0.8
RECENCY_WEIGHT = 0.2

# Chat & Streaming
CHAT_HISTORY_SIZE = 5
STREAMING_CHUNK_SIZE = 50
STREAMING_DELAY = 0.05

# Redis Chat Index
CHAT_IDX_PREFIX = 'chat:'
CHAT_IDX_NAME = 'idx:chat'
