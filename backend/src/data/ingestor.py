import yfinance as yf
from newspaper import Article
from src.data.datatabase import save_data,connect_db
import re

class YahooIngestor:
    def __init__(self, tickers):
        self.tickers = tickers
    
    def fetch(self):
        articles = []
        collection = connect_db()
        for t in self.tickers:
            ticker = yf.Ticker(t)

            for item in ticker.news[:10000]:
                try:
                    url = item["content"]["canonicalUrl"]["url"]
                    if not url:
                        continue

                    article = Article(url)
                    article.download()
                    article.parse()
                    doc = {
                        "id": item["content"]["id"],
                        "title": item["content"]["title"],
                        "text": article.text,
                        "date": article.publish_date,
                        "url": url
                    }
                    articles.append(doc)
                    save_data(doc,collection)
                    
                except:
                    continue
            

        return articles
    


    def chunk_text(self, text, size=300, overlap=50):
        sentences = re.split(r'(?<=[.!?]) +', text)  # split by sentences
        
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= size:
                current_chunk += " " + sentence
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    