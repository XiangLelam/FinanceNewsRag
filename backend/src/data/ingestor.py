import os
import requests
import trafilatura
import time
from dotenv import load_dotenv
from langdetect import detect
from datetime import datetime, timedelta, timezone
import src.config.constant as cons

load_dotenv()
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")

_last_gdelt_request = 0.0
_gdelt_blocked_until = 0.0


FINANCE_TERMS = {"stock", "stocks", "share", "shares", "price", "prices", "valuation", "market"}
class Ingestor:
    def __init__(self, query):
        self.max_results = cons.GDELT_MAX_RESULTS
        self.query = query
        self.url = cons.GDELT_URL

    def url_request(self, params, retries=3):
        global _last_gdelt_request
        headers = cons.HEADERS

        for attempt in range(retries):
            wait = cons.GDELT_MIN_INTERVAL - (time.time() - _last_gdelt_request)
            if wait > 0:
                time.sleep(wait)

            try:
                _last_gdelt_request = time.time()
                res = requests.get(
                    self.url,
                    params=params,
                    headers=headers,
                    timeout=cons.REQUEST_TIMEOUT
                )

                if res.status_code == 200 and res.text.strip().startswith("{"):
                    return res

                print(f"Attempt {attempt+1} failed: HTTP {res.status_code} {res.text[:80]}")

            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt+1} failed:", e)

            _last_gdelt_request = time.time() + cons.GDELT_MIN_INTERVAL * (2 ** attempt - 1)

        global _gdelt_blocked_until
        _gdelt_blocked_until = time.time() + cons.GDELT_COOLDOWN
        print(f"GDELT request failed after retries - skipping GDELT for {cons.GDELT_COOLDOWN}s")
        return None

    def get_gdelt_urls(self):
        remaining = _gdelt_blocked_until - time.time()
        if remaining > 0:
            print(f"GDELT unavailable (cooling down for {remaining:.0f}s more) - skipping")
            return []

        print(f"GDELT Query: '{self.query}'")
        params = {
            "query": f"{self.query} sourceLang:eng",
            "mode": "artlist",
            "maxrecords": self.max_results,
            "format": "json",
            "sort": cons.GDELT_SORT,
            "timespan": cons.GDELT_TIMESPAN
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

    def build_gnews_query(self, keywords):
        """Require the topic words, but accept any finance term: "apple stock price" -> apple AND (stock OR shares)."""
        words = [w.strip('"\'()') for w in keywords.lower().split()]
        words = [w for w in words if w and w not in ("and", "or", "not")]
        topic = [f'"{w}"' for w in words if w not in FINANCE_TERMS]
        has_finance = any(w in FINANCE_TERMS for w in words)

        if not topic:
            return "stock OR shares" if has_finance else keywords
        query = " AND ".join(topic)
        if has_finance:
            query += " AND (stock OR shares)"
        return query

    def get_gnews_urls(self):
        """Fallback news source when GDELT is unavailable (e.g. rate limited)."""
        if not GNEWS_API_KEY:
            print("GNEWS_API_KEY not set - skipping GNews fallback")
            return []

        gnews_query = self.build_gnews_query(self.query)
        print(f"GNews Query: '{gnews_query}'")
        since = datetime.now(timezone.utc) - timedelta(days=cons.GNEWS_DAYS)
        params = {
            "q": gnews_query,
            "in": "title,description",
            "lang": "en",
            "max": cons.GNEWS_MAX_RESULTS,
            "sortby": "relevance",
            "from": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "apikey": GNEWS_API_KEY
        }

        try:
            res = requests.get(cons.GNEWS_URL, params=params, timeout=cons.REQUEST_TIMEOUT)
            if res.status_code != 200:
                print(f"GNews request failed: HTTP {res.status_code} {res.text[:100]}")
                return []
            data = res.json()
        except Exception as e:
            print(f"GNews request failed: {str(e)[:100]}")
            return []

        articles = [
            {
                "title": a.get("title"),
                "url": a.get("url"),
                "source": (a.get("source") or {}).get("name"),
                "lang": "English",
                "date": a.get("publishedAt")
            }
            for a in data.get("articles", [])
            if a.get("url")
        ]

        print(f"GNews returned {len(articles)} articles")
        for i, a in enumerate(articles[:3], 1):
            print(f"{i}. {(a.get('title') or 'N/A')[:60]}...")

        return articles

    def is_english(self, text):
        try:
            return detect(text) == "en"
        except:
            return False

    def format_date(self, raw_date):
        if not raw_date:
            return None

        try:
            return datetime.strptime(raw_date, "%Y%m%dT%H%M%SZ")
        except ValueError:
            pass

        try:
            return datetime.strptime(raw_date, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass

        print(f"Unknown date format: {raw_date}")
        return None

    def scrape_article(self, url, query=None):
        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return None

            text = trafilatura.extract(downloaded)

            if not text or not self.is_english(text):
                return None
            
            if query:
                query_lower = query.lower().strip('\"').strip()
                text_lower = text.lower()
                
                # Extract keywords from query (remove common words and quotes)
                keywords = [w.strip('\"').strip() for w in query_lower.split() if len(w.strip('\"').strip()) >= cons.MIN_KEYWORD_LENGTH]

                # Check if at least one significant keyword appears in article
                found_keywords = [kw for kw in keywords if kw in text_lower]

                if keywords and not found_keywords:
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
        articles = self.get_gnews_urls()

        if not articles:
            print(f"GNews returned nothing for '{self.query}' - trying GDELT...")
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