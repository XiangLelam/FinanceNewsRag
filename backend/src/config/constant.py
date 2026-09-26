# HTTP & API Configuration
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
REQUEST_TIMEOUT = 10

# GDELT Data Ingestion
GDELT_MAX_RESULTS = 20
GDELT_FALLBACK_QUERY = "stock market news"
GDELT_MIN_INTERVAL = 6
GDELT_TIMESPAN = "7d"
GDELT_SORT = "HybridRel"
GDELT_COOLDOWN = 300

GNEWS_URL = "https://gnews.io/api/v4/search"
GNEWS_MAX_RESULTS = 10
GNEWS_DAYS = 7
MIN_KEYWORD_LENGTH = 3
ARTICLE_SNIPPET_LENGTH = 1000

# Text Processing & Chunking
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# RAG Scoring & Retrieval
EMBEDDING_MODEL = "multi-qa-MiniLM-L6-cos-v1"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CONFIDENCE_THRESHOLD = 0.5
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
