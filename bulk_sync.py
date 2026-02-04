import os
import time
from dotenv import load_dotenv
from supabase import create_client, Client
import trafilatura
from trafilatura.sitemaps import sitemap_search

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TARGET_URL = os.getenv("TARGET_URL")
IGNORE_PATTERNS = [p.strip() for p in os.getenv("IGNORE_PATTERNS", "").split(",") if p.strip()]

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Missing Supabase credentials in .env")
    exit(1)

if not TARGET_URL or "PLACEHOLDER" in TARGET_URL:
    print("Error: TARGET_URL is not set in .env. Please update it with the actual website URL.")
    exit(1)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def sync_article(url):
    print(f"Processing: {url}")
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        print(f"  - Failed to download: {url}")
        return

    # Extract metadata and content
    # include_comments=False, include_tables=True, no_fallback=False
    data = trafilatura.extract(downloaded, output_format='json', with_metadata=True, include_comments=False)
    
    if not data:
        # Fallback: try raw text extraction if JSON fails or returns nothing useful
        text = trafilatura.extract(downloaded)
        if text:
            # Minimal data structure if full metadata fails
            save_to_supabase({
                "source_url": url,
                "title": "Unknown Title", 
                "author": None,
                "full_body_text": text,
                "published_at": None 
            })
            print(f"  - Synced (Text Only): {url}")
        else:
            print(f"  - Failed to extract content: {url}")
        return

    import json
    article_data = json.loads(data)
    
    # Prepare payload
    payload = {
        "source_url": url,
        "title": article_data.get("title"),
        "author": article_data.get("author"),
        "full_body_text": article_data.get("text"), # 'text' field contains the main body
        "published_at": article_data.get("date"),
    }
    
    save_to_supabase(payload)
    print(f"  - Synced: {article_data.get('title', 'No Title')} ({url})")

def save_to_supabase(payload):
    try:
        # Upsert: Match on 'source_url' (must be unique in DB)
        # ignore_duplicates=False means update if exists
        supabase.table("articles").upsert(payload, on_conflict="source_url").execute()
    except Exception as e:
        print(f"  - Database Error: {e}")

def main():
    print(f"Starting Bulk Sync for: {TARGET_URL}")
    
    # 1. Discover URLs via Sitemap
    print("Scanning sitemap...")
    urls = sitemap_search(TARGET_URL)
    
    if not urls:
        print("No URLs found in sitemap. Attempting homepage crawl is not implemented in this minimal version.")
        print("Please ensure the target site has an accessible sitemap.")
        return

    print(f"Found {len(urls)} URLs. Starting sync...")
    
    for url in urls:
        # Check ignore patterns
        if any(pattern in url for pattern in IGNORE_PATTERNS):
            print(f"  - Skipped (Ignored): {url}")
            continue
            
        sync_article(url)
        time.sleep(1) # Polite delay

    print("Bulk sync complete.")

if __name__ == "__main__":
    main()
