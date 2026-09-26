from src.data.ingestor import Ingestor
from src.data.vectordb import VectorDB
from langchain_text_splitters import RecursiveCharacterTextSplitter
import src.config.constant as cons

class KnowledgeProcessing:
    def __init__(self, query):
        self.query = query

    def chunk_text(self, text):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=cons.CHUNK_SIZE,
            chunk_overlap=cons.CHUNK_OVERLAP
        )
        return splitter.split_text(text)

    def update_knowledge(self):
        """Fetch latest articles and rebuild vector DB. Returns True if successful."""
        print("Fetching latest news...")
        try:
            ingestor = Ingestor(self.query)
            articles = ingestor.fetch_context_for_query()

            if not articles:
                print("No articles fetched - cannot update KB")
                return False
            
            print(f"Fetched {len(articles)} articles, chunking...")

            all_chunks = []

            for i, article in enumerate(articles, 1):
                chunks = self.chunk_text(article["content"])
                print(f"Article {i}: {len(chunks)} chunks from '{article.get('title', 'N/A')[:50]}...'")

                for chunk in chunks:
                    all_chunks.append({
                        "text": chunk,
                        "url": article["url"],
                        "date": article.get("date"),
                        "title": article.get("title")
                    })

            if not all_chunks:
                print("No chunks created from articles")
                return False

            print(f"Total chunks: {len(all_chunks)}")
            
            vectordb = VectorDB()
            vectordb.build(all_chunks)
            vectordb.save()

            print(f"Knowledge base updated: {len(all_chunks)} chunks from {len(articles)} articles")
            return True
        
        except Exception as e:
            print(f"Error updating knowledge base: {e}")
            import traceback
            traceback.print_exc()
            return False