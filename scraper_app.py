import streamlit as st
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from urllib.parse import urljoin, urlparse
import time
import pandas as pd
from datetime import datetime

# --- CONFIGURATION & STATE ---
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'stats' not in st.session_state:
    st.session_state.stats = {'found': 0, 'added': 0, 'updated': 0, 'errors': 0}

def log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    st.session_state.logs.append(entry)
    # Keep log size manageable
    if len(st.session_state.logs) > 100:
        st.session_state.logs.pop(0)

# --- SCRAPING LOGIC ---
def is_valid_url(url, base_domain):
    parsed = urlparse(url)
    # Strict domain check and ignore common non-content paths
    is_domain = bool(parsed.netloc) and base_domain in parsed.netloc
    is_junk = any(x in url.lower() for x in ['login', 'signup', 'register', 'search', 'video', 'advertisement'])
    return is_domain and not is_junk

def scrape_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Heuristic: Detect if this is an Article or a Landing/Listing Page
        # Articles usually have many Paragraphs <p>
        paragraphs = soup.find_all('p')
        text_length = sum(len(p.get_text()) for p in paragraphs)
        
        if text_length < 500:
            # If text is too short, it's likely a navigation/category page, NOT an article.
            # We return None so we don't save it, but the Crawler will still find links on it.
            return None

        title = soup.title.string.strip() if soup.title else "No Title"
        
        # improved content extraction for BabyCenter/General
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
                # Extract text with newlines
                content_text = candidate.get_text(separator='\n', strip=True)
                if len(content_text) > 500: # Found a good candidate
                    break
        
        if not content_text:
            return None
            
        return {
            'url': url,
            'title': title,
            'content': content_text,
            'source_domain': urlparse(url).netloc
        }
    except Exception as e:
        log(f"Error scraping {url}: {e}")
        return None

def run_crawler(start_url, supabase_url, supabase_key):
    if not start_url or not supabase_url or not supabase_key:
        st.error("Missing URL or Credentials")
        return

    try:
        supabase: Client = create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"Failed to connect to Supabase: {e}")
        return

    # Use a set for visited to prevent loops (O(1) lookup)
    visited = set()
    
    # Priority Queue approach: [URL, Depth]
    # We prioritize "See All" pages to ensure we get lists early
    queue = [start_url]
    
    base_domain = urlparse(start_url).netloc

    placeholder = st.empty()
    st.info(f"🚀 Starting Deep Crawl on: {base_domain}")
    
    while queue and st.session_state.is_running:
        current_url = queue.pop(0)
        
        if current_url in visited:
            continue
            
        visited.add(current_url)
        
        # UI Feedback
        log(f"Crawling: {current_url}")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(current_url, headers=headers, timeout=10)
            if response.status_code != 200: 
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # --- LINK DISCOVERY STRATEGY ---
            # 1. Expand "See all" and "Topic" links (Push to FRONT of queue to drill down first)
            # 2. Add normal article links (Push to BACK of queue)
            
            prio_links = []
            normal_links = []
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(current_url, href)
                
                if not is_valid_url(full_url, base_domain) or full_url in visited:
                    continue
                
                link_text = link.get_text().lower()
                
                # Heuristic: "See all", "topics", "week" are high priority navigation paths
                if 'see all' in link_text or 'topic' in link_text or 'week' in link_text or 'trimester' in link_text:
                    prio_links.append(full_url)
                else:
                    normal_links.append(full_url)
            
            # Add to queue: Priority first (Depth First), then Normal
            for link in prio_links:
                if link not in queue: queue.insert(0, link) # DFS for topics
                
            for link in normal_links:
                if link not in queue: queue.append(link) # BFS for foliage

            # --- SAVE CONTENT STRATEGY ---
            # Extract content from current page
            article_data = scrape_content(current_url)
            
            if article_data:
                st.session_state.stats['found'] += 1
                
                # Upsert to Supabase
                try:
                    data, count = supabase.table('scraped_articles').upsert(
                        article_data, on_conflict='url'
                    ).execute()
                    
                    st.session_state.stats['added'] += 1
                    log(f"✅ Saved: {article_data['title'][:40]}...")
                         
                except Exception as db_err:
                    st.session_state.stats['errors'] += 1
                    log(f"❌ DB Error: {db_err}")

            # Update UI Stats
            with placeholder.container():
                col1, col2, col3 = st.columns(3)
                col1.metric("URLs Visited", len(visited), delta=1)
                col2.metric("Articles Saved", st.session_state.stats['added'], delta=st.session_state.stats['found'] - st.session_state.stats['added'])
                col3.metric("Queue Size", len(queue))
        
        except Exception as e:
            log(f"Error processing {current_url}: {e}")

        # Rate Limiting
        time.sleep(0.5)

    st.session_state.is_running = False
    log("Crawler stopped. (User stopped or Queue empty)")

# --- UI LAYOUT ---
st.set_page_config(page_title="Iron Niti Scraper", page_icon="🕷️", layout="wide")

st.title("🕷️ Web Scraping Automation Dashboard")

# Sidebar: Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    target_url = st.text_input("Target Website URL", "https://www.babycenter.com/pregnancy")
    
    st.subheader("Supabase Credentials")
    su_url = st.text_input("Project URL", placeholder="https://xyz.supabase.co")
    su_key = st.text_input("Service Role Key", type="password")
    
    st.info("These credentials can be updated anytime.")
    
    st.markdown("---")
    
    if st.button("🛑 STOP Automation", type="primary"):
        st.session_state.is_running = False
        st.warning("Stopping crawler...")

# Main Area
col_main, col_logs = st.columns([2, 1])

with col_main:
    st.subheader("Control Center")
    if st.button("▶️ Start Automation", use_container_width=True):
        if not su_url or not su_key:
            st.error("Please enter Supabase URL and Key in the sidebar!")
        else:
            st.session_state.is_running = True
            st.success("Automation Started! Processing...")
            run_crawler(target_url, su_url, su_key)

    st.subheader("Database Schema")
    with st.expander("View SQL Code for Supabase"):
        st.code("""
-- Run this in Supabase SQL Editor
CREATE TABLE IF NOT EXISTS scraped_articles (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    content TEXT,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source_domain TEXT,
    status TEXT DEFAULT 'active'
);
        """, language="sql")

    st.subheader("Live Statistics")
    # Stats metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Articles Found", st.session_state.stats['found'])
    m2.metric("Saved/Updated", st.session_state.stats['added'])
    m3.metric("Errors", st.session_state.stats['errors'])

with col_logs:
    st.subheader("📜 Activity Log")
    log_container = st.container(height=500)
    with log_container:
        for l in reversed(st.session_state.logs):
            st.text(l)
