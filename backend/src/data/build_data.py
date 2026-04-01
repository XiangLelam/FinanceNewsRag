from src.data.ingestor import YahooIngestor
from src.data.vectordb import VectorDB

ingestor = YahooIngestor(["AAPL","TSLA","MSFT"])
articles = ingestor.fetch()

all_chunks = []

for article in articles:
    chunks = ingestor.chunk_text(article["text"])
    all_chunks.extend(chunks)
vectordb = VectorDB()
vectordb.build(all_chunks)
vectordb.save()

def update_knowledge():
        print("🔄 Fetching latest news...")

        ingestor = YahooIngestor(["AAPL","TSLA","MSFT"])
        articles = ingestor.fetch()

        all_chunks = []
        for article in articles:
            chunks = ingestor.chunk_text(article["text"])
            all_chunks.extend(chunks)

        vectordb = VectorDB()
        vectordb.build(all_chunks)
        vectordb.save()

        print("✅ Knowledge base updated")