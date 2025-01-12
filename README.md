# ScrapeScout

**If you find this project helpful, please give the repo a star!** Every star helps us reach more developers and maintainers in need of a powerful, flexible search and scraping tool.

## Overview
ScrapeScout is a Python-based application that:
- Uses **Google Custom Search** (or other engines) to find relevant articles within specified domains.
- Optionally scrapes their content or downloads PDF files.
- Organizes output in Excel, Markdown files, and a SQLite database for easy retrieval and analysis.

---

## Directory Structure


1. **`config-example.yaml`** – Rename to **`config.yaml`** and adjust settings for your environment.  
2. **`main.py`** – High-level logic for loading config, searching, scraping, storing, etc.  
3. **`storage.py`** – Functions for persisting data (DB, Excel, Markdown).  
4. **`utils/logger.py`** – Central logging config via **loguru**.  
5. **`requirements.txt`** – Lists all dependencies for quick setup.

---

## Getting Started

1. **Clone the Repo & Install Dependencies**  
   ```bash
   git clone https://github.com/YourUsername/scrapescout.git
   cd scrapescout
   pip install -r requirements.txt
    ```

2.  **Rename and Update the Config File**
    
    1.  Copy **`config-example.yaml`** to **`config.yaml`**:
        
        ```bash
        cp config-example.yaml config.yaml
        ```
        
    2.  Open `config.yaml` and edit:
        *   **search engine credentials** (e.g., `api_key`, `cx` for Google).
        *   **dateRestrict** or other parameters (e.g., `"y5"` for 5 years).
        *   **paths** for output storage (Markdown, Excel, DB).
3.  **Run the Application**
    
    ```bash
    python main.py
    ```
    
*   This will **search** your domains based on `config.yaml`, **deduplicate** if enabled, **store** initial results in DB & Excel, and **scrape** articles (if `scrape_articles` is `"yes"`).

* * *

Updating the Excel Files
------------------------

You should have two **input Excel files** referenced in your `config.yaml`:

*   **`topics.xlsx`** (or your chosen filename)
*   **`domains.xlsx`** (or your chosen filename)

### Topics Excel

*   **Columns**: `topic_name`
*   **Purpose**: Provide a list of query terms or topics to search for.
*   **Add** any new topic to the `topic_name` column to have the app search for it on the next run.

### Domains Excel

*   **Columns**:
    *   `source_name`
    *   `source_domain`
    *   `source_max_articles`
*   **Purpose**: Specify each domain you’d like to search, its friendly name, and the maximum number of articles you’d like the script to retrieve from that domain.
*   **Add** or **remove** rows to include or exclude domains. Increase or decrease `source_max_articles` to control how many articles per domain you retrieve.

**Note**: Make sure these filenames, sheet names, and column names match exactly with what is configured in `config.yaml`.

* * *

Configuration Details
---------------------

*   **`scrape_articles`**: `yes` or `no`.
    *   If `yes`, each URL is scraped or PDF is downloaded; if `no`, only metadata is stored.
*   **`search_engine_selection`**: e.g., `"google"`.
*   **`dateRestrict`** (e.g., `"y5"`): Only return results from the last 5 years, or use `m6`, `d7`, etc.
*   **`output_markdown.path`**: Where Markdown articles (or PDFs) are saved.
*   **`db_storage.name`** & **`db_storage.path`**: SQLite file name and location.
*   **`output_excel.file_name`** & **`output_excel.path`**: Excel output file name and location.

* * *

Contributing
------------

1.  **Fork** the repo.
2.  **Create** your feature branch (`git checkout -b feature/my-feature`).
3.  **Commit** your changes (`git commit -am 'Add some feature'`).
4.  **Push** to the branch (`git push origin feature/my-feature`).
5.  **Open a Pull Request**.

We welcome bug reports, feature requests, and community contributions!

* * *

License
-------

This project is licensed under the MIT License.

* * *

Thank You
---------

Thank you for checking out ScrapeScout! Remember to **⭐ star** the repo if you enjoy using it or find it helpful. Your support helps us maintain and improve the code for everyone.

Happy scraping!