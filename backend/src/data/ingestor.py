import requests
import trafilatura
import time
from langdetect import detect
from datetime import datetime
import src.config.constant as cons

class Ingestor:
    def __init__(self, query):
        self.max_results = cons.GDELT_MAX_RESULTS
        self.query = query
        self.url = cons.GDELT_URL

    def url_request(self, params, retries=3):
        headers = cons.HEADERS

        for attempt in range(retries):
            try:
                res = requests.get(
                    self.url,
                    params=params,
                    headers=headers,
                    timeout=cons.REQUEST_TIMEOUT
                )

                if res.status_code == 200 and res.text.strip():
                    return res

            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt+1} failed:", e)
                time.sleep(2)

        print("GDELT request failed after retries")
        return None

    def get_gdelt_urls(self):
        print(f"GDELT Query: '{self.query}'")
        params = {
            "query": f"{self.query} sourceLang:eng",
            "mode": "artlist",
            "maxrecords": self.max_results,
            "format": "json"
        }

        print(f"GDELT URL: {self.url}")
        print(f"Params: {params}")
        
        res = self.url_request(params)

        if not res:
            print(f"GDELT API request failed")
            return []

        try:
            data = res.json()
        except Exception as e:
            print(f"Invalid JSON from GDELT: {str(e)[:100]}")
            return []
        
        articles = [
            {
                "title": a.get("title"),
                "url": a.get("url"),
                "source": a.get("domain"),
                "lang": a.get("language"),
                "date": a.get("seendate") 
            }
            for a in data.get("articles", [])
            if a.get("language") == "English"
        ]
        
        print(f"GDELT returned {len(articles)} articles")
        for i, a in enumerate(articles[:3], 1):
            print(f"{i}. {a.get('title', 'N/A')[:60]}...")
        
        return articles

    def is_english(self, text):
        try:
            return detect(text) == "en"
        except:
            return False

    def format_date(self,raw_date):
        try:
            return datetime.strptime(raw_date, "%Y%m%d%H%M%S")
        except:
            return None

    def scrape_article(self, url, query=None):
        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return None

            text = trafilatura.extract(downloaded)

            if not text or not self.is_english(text):
                return None
            
            # Entity validation: ensure article mentions the search term
            if query:
                query_lower = query.lower().strip('\"').strip()
                text_lower = text.lower()
                
                # Extract keywords from query (remove common words and quotes)
                keywords = [w.strip('\"').strip() for w in query_lower.split() if len(w.strip('\"').strip()) > cons.MIN_KEYWORD_LENGTH]
                
                # Check if at least one significant keyword appears in article
                found_keywords = [kw for kw in keywords if kw in text_lower]
                
                if not found_keywords:
                    print(f"Skipped (no keywords match): {keywords} not in article")
                    return None
                
                text_snippet = (text[:cons.ARTICLE_SNIPPET_LENGTH]).lower()
                keyword_count = sum(1 for kw in found_keywords if kw in text_snippet)
                
                if keyword_count == 0:
                    print(f"Skipped (keyword not in intro): {found_keywords}")
                    return None
                
                print(f"Matched keywords: {found_keywords}")

            return text

        except Exception as e:
            print(f"Scraping failed: {url}: {str(e)[:50]}")
            return None


    def fetch_context_for_query(self):
        """Fetch articles for the query. Returns list of parsed articles with content."""
        articles = self.get_gdelt_urls()
        
        if not articles:
            print(f"No articles found for query: '{self.query}' - trying fallback...")
            self.query = cons.GDELT_FALLBACK_QUERY
            articles = self.get_gdelt_urls()
        
        if not articles:
            print("No articles found even with fallback")
            return []
        
        print(f"Found {len(articles)} articles, attempting to scrape...")
        
        articles = sorted(
            articles,
            key=lambda x: x.get("date") or "",
            reverse=True
        )

        context_data = []
        exist_url = set()
        scrape_attempts = 0
        successful_scrapes = 0
        skipped_count = 0
        
        for article in articles:
            article_url = article["url"]
            
            if article_url in exist_url:
                continue
            
            exist_url.add(article_url)
            scrape_attempts += 1
            
            text = self.scrape_article(article_url, query=self.query)

            if text:
                successful_scrapes += 1
                context_data.append({
                    "title": article["title"],
                    "url": article_url,
                    "content": text,
                    "date": self.format_date(article["date"])
                })
            else:
                skipped_count += 1
        
        print(f"Successfully scraped {successful_scrapes}/{scrape_attempts} articles ({skipped_count} skipped due to relevance filtering)")
        return context_data