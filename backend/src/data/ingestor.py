import requests
import trafilatura
import time
from langdetect import detect
from datetime import datetime

class Ingestor:
    def __init__(self, query):
        self.max_results = 5
        self.query = query
        self.url = "https://api.gdeltproject.org/api/v2/doc/doc"

    def safe_request(self, params, retries=3):
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        for attempt in range(retries):
            try:
                res = requests.get(
                    self.url,
                    params=params,
                    headers=headers,
                    timeout=10
                )

                if res.status_code == 200 and res.text.strip():
                    return res

            except requests.exceptions.RequestException as e:
                print(f"⚠️ Attempt {attempt+1} failed:", e)
                time.sleep(2)

        print("❌ GDELT request failed after retries")
        return None

    def get_gdelt_urls(self):
        params = {
            # 🔥 English filter added here
            "query": f"{self.query} sourceLang:eng",
            "mode": "artlist",
            "maxrecords": self.max_results,
            "format": "json"
        }

        res = self.safe_request(params)

        if not res:
            return []

        try:
            data = res.json()
        except:
            print("❌ Invalid JSON:", res.text[:200])
            return []

        # extra safety filter
        return [
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

    def scrape_article(self, url):
        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return None

            text = trafilatura.extract(downloaded)

            # 🔥 filter non-English scraped content
            if text and self.is_english(text):
                return text

            return None

        except Exception as e:
            print(f"⚠️ Scraping failed: {url}", e)
            return None


    def fetch_context_for_query(self):
        articles = self.get_gdelt_urls()

        # fallback if empty
        if not articles:
            print("⚠️ Using fallback query...")
            self.query = "stock market news"
            articles = self.get_gdelt_urls()
        articles = sorted(
            articles,
            key=lambda x: x.get("date") or "",
            reverse=True
        )

        context_data = []
        exist_url = set()
        for article in articles:
            article_url = article["url"]
            if  article_url not in exist_url:
                text = self.scrape_article(article_url)
                exist_url.add(article_url)
            else:
                continue

            if text:
                context_data.append({
                    "title": article["title"],
                    "url": article_url,
                    "content": text,  # truncate for LLM
                    "date": self.format_date(article["date"])
                })
        return context_data