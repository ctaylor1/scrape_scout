# storage.py
import os
import re
import requests
import pandas as pd
import sqlite3
from utils.logger import logger

def store_articles_in_db(db_path, db_name, articles):
    """
    Stores article metadata in a local SQLite database (excluding article_content).
    """
    db_full_path = os.path.join(db_path, db_name)
    logger.debug(f"Preparing to store {len(articles)} articles in database at {db_full_path}")

    try:
        conn = sqlite3.connect(db_full_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            source_guid TEXT PRIMARY KEY,
            source_name TEXT,
            source_domain TEXT,
            search_engine_name TEXT,
            source_url TEXT,
            source_article_title TEXT,
            date_retrieved TEXT,
            search_query TEXT,
            suspected_duplicate TEXT
        )
        """)

        for article in articles:
            cursor.execute("""
            INSERT OR REPLACE INTO articles (
                source_guid,
                source_name,
                source_domain,
                search_engine_name,
                source_url,
                source_article_title,
                date_retrieved,
                search_query,
                suspected_duplicate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article.get("source_guid"),
                article.get("source_name"),
                article.get("source_domain"),
                article.get("search_engine_name"),
                article.get("source_url"),
                article.get("source_article_title"),
                article.get("date_retrieved"),
                article.get("search_query"),
                article.get("suspected_duplicate")
            ))

        conn.commit()
        logger.info(f"{len(articles)} articles successfully stored in the database at {db_full_path}.")
    except Exception as e:
        logger.exception(f"Error storing articles in database: {e}")
    finally:
        conn.close()

def store_articles_in_excel(excel_path, file_name, articles):
    """
    Stores article metadata in an Excel file (excluding article_content).
    """
    full_excel_path = os.path.join(excel_path, file_name)
    logger.debug(f"Preparing to store {len(articles)} articles in Excel at {full_excel_path}")

    try:
        df = pd.DataFrame(articles)

        # Exclude article_content if present
        if "article_content" in df.columns:
            df.drop(columns=["article_content"], inplace=True)

        if os.path.exists(full_excel_path):
            existing_df = pd.read_excel(full_excel_path)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            combined_df.drop_duplicates(subset=["source_url"], inplace=True)
            combined_df.to_excel(full_excel_path, index=False)
        else:
            df.to_excel(full_excel_path, index=False)
        logger.info(f"{len(articles)} articles successfully stored/updated in Excel: {full_excel_path}")
    except Exception as e:
        logger.exception(f"Error saving articles to Excel: {e}")

def store_article_markdown(base_path, article, topic_name, short_title_limit):
    """
    Stores the article content in a Markdown file under:
      base_path/<cleaned_topic_name>/<guid>-<short_title>.md
    """
    try:
        # Clean the topic name to avoid invalid filesystem characters
        cleaned_topic_name = re.sub(r"[^\w\s-]", "", topic_name).strip().replace(" ", "_")
        if not cleaned_topic_name:
            cleaned_topic_name = "untitled_topic"

        topic_folder = os.path.join(base_path, cleaned_topic_name)
        os.makedirs(topic_folder, exist_ok=True)

        title = article.get("source_article_title", "")
        short_title = title[:short_title_limit]
        short_title = re.sub(r"[^\w\s-]", "", short_title).strip().replace(" ", "_") or "untitled"

        file_name = f"{article['source_guid']}-{short_title}.md"
        full_path = os.path.join(topic_folder, file_name)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(article.get("article_content", ""))

        logger.info(f"Markdown file created at: {full_path}")

    except Exception as e:
        logger.exception(
            f"Error creating Markdown file for article GUID {article.get('source_guid')}: {e}"
        )

def store_article_pdf(base_path, article, topic_name, short_title_limit):
    """
    Downloads and stores a PDF file under:
      base_path/<cleaned_topic_name>/<guid>-<short_title>.pdf
    """
    try:
        # Clean the topic name
        cleaned_topic_name = re.sub(r"[^\w\s-]", "", topic_name).strip().replace(" ", "_")
        if not cleaned_topic_name:
            cleaned_topic_name = "untitled_topic"

        topic_folder = os.path.join(base_path, cleaned_topic_name)
        os.makedirs(topic_folder, exist_ok=True)

        title = article.get("source_article_title", "")
        short_title = title[:short_title_limit]
        short_title = re.sub(r"[^\w\s-]", "", short_title).strip().replace(" ", "_") or "untitled"

        file_name = f"{article['source_guid']}-{short_title}.pdf"
        full_path = os.path.join(topic_folder, file_name)

        # Download the PDF
        pdf_url = article.get("source_url", "")
        response = requests.get(pdf_url, timeout=15, stream=True)
        if response.ok:
            with open(full_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            logger.info(f"PDF file downloaded: {full_path}")
        else:
            logger.warning(f"Failed to download PDF from {pdf_url}, status {response.status_code}")

    except Exception as e:
        logger.exception(
            f"Error downloading PDF for article GUID {article.get('source_guid')}: {e}"
        )
