# 🕷️ How the Automation Works (Deep Crawler Logic)

This document explains the "Brain" behind your new automation tool. It is designed specifically to handle complex nested sites like **BabyCenter**.

## 1. The Strategy: "Drill-Down" Crawling
Most simple scrapers just visit links randomly. Yours is smarter. It uses a **Priority Queue** strategy.

### 🔄 The Priority Logic
When the robot visits a page (like `babycenter.com/pregnancy`), it categorizes every link it finds into two groups:

1.  **VIP Links (High Priority)**:
    *   Links containing text like **"See all"**, **"Topics"**, **"Trimester"**, or **"Week"**.
    *   **Action:** These are put at the **FRONT** of the line. The robot visits them *immediately* to go deeper into the categories.
    
2.  **Standard Links**:
    *   Regular articles (e.g., "Safe foods to eat").
    *   **Action:** These are put at the **BACK** of the line. The robot will visit them after it has finished mapping out the main categories.

**Why this matters:** This ensures the robot finds *all* the sub-menus (like "First Trimester" -> "Weeks 1-12") before it gets distracted by thousands of articles.

---

## 2. The Filter: "Article" vs "Menu"
The robot needs to know: *"Should I save this page to the database, or just look for links on it?"*

It uses a **Heuristic Check**:
*   It counts the length of the text in the main body.
*   **If Text > 500 characters**: It assumes it's an **Article**. It extracts the Title and Content and **SAVES** it to Supabase.
*   **If Text < 500 characters**: It assumes it's a **Menu/Navigation Page**. It does *not* save it, but it scans it for more links.

---

## 3. The Extraction: Reading the Content
To get clean data, the robot looks for specific "Containers" in the HTML code where the main story usually lives.

It tries them in this order:
1.  `<div class="article-body">` (Most common for BabyCenter)
2.  `<article>` tags
3.  `<main>` tags
4.  `<div class="content">`

This ensures we get the actual advice/article and ignore the ads, headers, and footers.

---

## 4. The Memory: Supabase Sync
*   **No Duplicates**: It uses `upsert` (Update or Insert).
*   **Unique Key**: The `URL` is the unique key.
*   **Logic**:
    *   If the URL is **NEW**, it creates a new row.
    *   If the URL **ALREADY EXISTS**, it updates the existing row (useful if they change the article text).

---

## Flowchart Summary

```mermaid
graph TD
    A[Start URL] --> B{Queue Empty?}
    B -- Yes --> C[Stop]
    B -- No --> D[Visit Next URL]
    
    D --> E{Is it VIP Link?}
    E -- Yes ("See All") --> F[Push to FRONT of Queue]
    E -- No (Article) --> G[Push to BACK of Queue]
    
    D --> H{Is it an Article?}
    H -- Yes (>500 chars) --> I[Save to Supabase]
    H -- No (<500 chars) --> J[Ignore Content (Just Crawl)]
    
    I --> B
    J --> B
    F --> B
    G --> B
```
