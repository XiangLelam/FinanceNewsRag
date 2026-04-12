from src.data.ingestor import Ingestor
from src.data.vectordb import VectorDB
from langchain_text_splitters import RecursiveCharacterTextSplitter

class KnowledgeProcessing:
    def __init__(self, query):
        self.query = query

    def chunk_text(self, text):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100
        )
        return splitter.split_text(text)

    def update_knowledge(self):
        print("🔄 Fetching latest news...")
        ingestor = Ingestor(self.query)
        articles = ingestor.fetch_context_for_query()

        all_chunks = []

        for article in articles:
            chunks = self.chunk_text(article["content"])

            for chunk in chunks:
                all_chunks.append({
                    "text": chunk,
                    "url": article["url"]
                })

        if not all_chunks:
            print("⚠️ No data fetched")
            return

        vectordb = VectorDB()
        vectordb.build(all_chunks)
        vectordb.save()

        print("✅ Knowledge base updated")