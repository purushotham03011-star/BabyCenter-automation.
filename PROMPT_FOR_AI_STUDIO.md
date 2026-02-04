You are an expert full-stack developer and automation engineer. I need you to build a robust web scraping and content aggregation automation tool with the following specifications:

### 1. The Core Objective
Create a user-friendly application (preferably using Python/Streamlit or Node.js/React) that takes a "Seed URL" (e.g., a specific category page like `babycenter.com/pregnancy`).
The system must:
*   **Deep Crawl**: Recursively visit all valid hyperlinks on that page (articles, "See All" lists, sub-categories).
*   **Extract Content**: For every article found, extract the Title, Main Text Body, and URL.
*   **Store Data**: Save this structured data into a Supabase database.
*   **Monitor Updates**: If run again, it should detect new articles or specific changes and update the database accordingly (Upsert logic).

### 2. User Interface (Dashboard) Requirements
The dashboard must include:
*   **Configuration Panel**: Input fields to dynamic set/update:
    *   Target Website URL.
    *   Supabase URL.
    *   Supabase Service Key.
*   **Database Setup**: A "View SQL Code" button that provides the ready-made SQL snippet to initialize the Supabase tables.
*   **Controls**:
    *   "Start Automation" button.
    *   "Stop/Pause" button.
*   **Live Status**: Real-time display showing:
    *   Current URL being crawled.
    *   Total Articles Found.
    *   New Articles Added vs. Existing Updated.
    *   A log console showing progress.

### 3. Technical Logic Requirements
*   **Depth Handling**: The scraper should handle pagination (e.g., "See All" buttons) and traverse at least 2-3 layers deep to find leaf-node articles.
*   **Robustness**: Handle network errors or timeouts gracefully without crashing.
*   **Deduping**: Ensure the same URL isn't added twice; update the existing record instead.

Please provide the full code for the frontend, backend, and the scraper logic.
