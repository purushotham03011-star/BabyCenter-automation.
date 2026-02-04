import os
import time
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv

# Load credentials from .env file
load_dotenv()

TARGET_URL = os.getenv("TARGET_URL", "https://www.babycenter.com/pregnancy")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: Missing credentials in .env file.")
    print("Please open .env and add SUPABASE_URL and SUPABASE_KEY")
    exit(1)

# Connect to DB
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def log(msg):
    print(f"[{time.strftime('%X')}] {msg}")

def is_valid_url(url, base_domain):
    parsed = urlparse(url)
    is_domain = bool(parsed.netloc) and base_domain in parsed.netloc
    is_junk = any(x in url.lower() for x in ['login', 'signup', 'register', 'search', 'video', 'advertisement'])
    return is_domain and not is_junk

def scrape_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200: return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Heuristic: Article Detection
        paragraphs = soup.find_all('p')
        text_length = sum(len(p.get_text()) for p in paragraphs)
        
        if text_length < 500: return None # Navigation page

        title = soup.title.string.strip() if soup.title else "No Title"
        
        content_candidates = [
            soup.find('div', class_='article-body'),
            soup.find('article'),
            soup.find('main'),
            soup.find('div', class_='content'),
            soup.body
        ]
        
        content_text = ""
        for candidate in content_candidates:
            if candidate:
                content_text = candidate.get_text(separator='\n', strip=True)
                if len(content_text) > 500: break
        
        if not content_text: return None
            
        return {
            'url': url,
            'title': title,
            'content': content_text,
            'source_domain': urlparse(url).netloc
        }
    except Exception as e:
        log(f"Error scraping {url}: {e}")
        return None

def run_background_crawl():
    log(f"🚀 Starting Background Automation for: {TARGET_URL}")
    
    visited = set()
    queue = [TARGET_URL]
    base_domain = urlparse(TARGET_URL).netloc
    
    stats = {'found': 0, 'added': 0}

    while queue:
        current_url = queue.pop(0)
        if current_url in visited: continue
        visited.add(current_url)
        
        log(f"Crawling: {current_url}")
        
        try:
            response = requests.get(current_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code != 200: continue
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Link Discovery
            prio_links = [] # 'See all', 'Topics'
            normal_links = []
            
            for link in soup.find_all('a', href=True):
                full_url = urljoin(current_url, link['href'])
                if not is_valid_url(full_url, base_domain) or full_url in visited: continue
                
                txt = link.get_text().lower()
                if 'see all' in txt or 'topic' in txt or 'week' in txt:
                    prio_links.append(full_url)
                else:
                    normal_links.append(full_url)
            
            # DFS Priority
            for l in prio_links: 
                if l not in queue: queue.insert(0, l)
            for l in normal_links:
                if l not in queue: queue.append(l)

            # Save Content
            data = scrape_content(current_url)
            if data:
                stats['found'] += 1
                try:
                    supabase.table('scraped_articles').upsert(data, on_conflict='url').execute()
                    stats['added'] += 1
                    log(f"✅ Upserted: {data['title'][:40]}...")
                except Exception as e:
                    log(f"❌ DB Error: {e}")

        except Exception as e:
            log(f"Error: {e}")
            
        time.sleep(0.5)

    log(f"🏁 Basic crawl finished. Found {stats['found']}, Added {stats['added']}")

if __name__ == "__main__":
    run_background_crawl()
