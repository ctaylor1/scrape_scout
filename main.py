# main.py
import os
import yaml
import uuid
import pandas as pd
import requests
import time
from datetime import datetime
from utils.logger import logger
from utils.storage import (
        store_articles_in_db,
        store_articles_in_excel,
        store_article_markdown,
        store_article_pdf,
        load_articles_from_db
)
from markdownify import markdownify

def search_articles(api_config, query, domain, max_articles, max_qpm):
    """
    Makes a single query to the Google Custom Search API,
    respecting max_queries_per_minute (QPM).
    """
    logger.debug(f"Searching articles for '{query}' on domain '{domain}' (max: {max_articles})")

    # Throttle (queries per minute)
    if max_qpm > 0:
        time.sleep(60.0 / max_qpm)

    articles = []
    params = {
        "key": api_config.get("api_key"),
        "cx": api_config.get("cx"),
        "q": query,
        "lr": "lang_en",
        "safe": "off",
        "siteSearch": domain,
        "siteSearchFilter": "i"
    }

    # Optional dateRestrict
    date_restrict_value = api_config.get("dateRestrict", "").strip()
    if date_restrict_value:
        params["dateRestrict"] = date_restrict_value

    try:
        response = requests.get(api_config.get("api_url"), params=params, timeout=10)
        logger.debug(f"Full Request URL: {response.url}")

        if response.ok:
            data = response.json()
            items = data.get("items", [])[:max_articles]
            for item in items:
                articles.append({
                    "source_guid": str(uuid.uuid4()),
                    "source_name": domain,
                    "source_domain": domain,
                    "search_engine_name": api_config.get("api_name"),
                    "source_url": item.get("link"),
                    "source_article_title": item.get("title"),
                    "search_query": query
                })
        else:
            logger.warning(f"Search API call failed with status {response.status_code}")
            logger.debug(f"Response text: {response.text}")
    except Exception as e:
        logger.exception(f"Error searching articles for {query} on {domain}: {e}")

    return articles

def main():
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Config variables
    search_engine_selection = config.get("search_engine_selection", "google")
    engines_config = config.get("search_engines", {})
    selected_engine_config = engines_config.get(search_engine_selection, {})

    search_settings = config.get("search_settings", {})
    max_qpm = search_settings.get("max_queries_per_minute", 100)   # queries per minute
    max_qpd = search_settings.get("max_queries_per_day", 10000)    # queries per day

    run_search = config.get("run_search", "yes").lower()  # "yes" or "no"
    scrape_engine_selection = config.get("scrape_engine_selection", "custom")
    scrape_flag = config.get("scrape_articles", "yes")
    deduplicate_flag = config.get("de_duplicate_articles", "off")

    markdown_settings = config.get("markdown_settings", {})
    short_title_limit = markdown_settings.get("short_title_limit", 15)

    db_path = config["db_storage"]["path"]
    db_name = config["db_storage"]["name"]
    excel_out_path = config["output_excel"]["path"]
    excel_out_file = config["output_excel"]["file_name"]
    markdown_out_path = config["output_markdown"]["path"]
    
    all_articles = []
    
    if run_search == "yes":
        logger.info("Running search logic...")

        # Load Topics
        topic_config = config.get("topics", {})
        topics_excel = os.path.join(topic_config["location"], topic_config["excel_file_name"])
        topics_df = pd.read_excel(topics_excel, sheet_name=topic_config["sheet_name"])
        topics_list = topics_df[topic_config["column_name"]].dropna().tolist()

        # Load Domains
        domain_config = config.get("domains", {})
        domains_excel = os.path.join(domain_config["location"], domain_config["excel_file_name"])
        domains_df = pd.read_excel(domains_excel, sheet_name=domain_config["sheet_name"])
        domains_records = domains_df.to_dict("records")

        # Perform your daily_count logic if needed
        daily_count = 0
        for topic in topics_list:
            if daily_count >= max_qpd:
                logger.info("Max daily queries reached. Stopping early.")
                break

            for domain_row in domains_records:
                if daily_count >= max_qpd:
                    logger.info("Max daily queries reached in domain loop.")
                    break

                domain_value = domain_row[domain_config["columns"]["domain"]]
                max_articles = domain_row[domain_config["columns"]["max_articles"]]

                found_articles = search_articles(
                    # your engine config, e.g. config["search_engines"]["google"]
                    config["search_engines"][config["search_engine_selection"]],
                    topic,
                    domain_value,
                    max_articles,
                    max_qpm
                )
                daily_count += 1

                # Deduplicate if needed (local or global)
                if deduplicate_flag == "on":
                    # deduplicate logic
                    unique_urls = set()
                    deduped_batch = []
                    for article in found_articles:
                        if article["source_url"] not in unique_urls:
                            article["suspected_duplicate"] = "no"
                            unique_urls.add(article["source_url"])
                            deduped_batch.append(article)
                        else:
                            article["suspected_duplicate"] = "yes"
                            deduped_batch.append(article)
                    found_articles = deduped_batch

                # Immediately store to DB & Excel
                store_articles_in_db(db_path, db_name, found_articles)
                store_articles_in_excel(excel_out_path, excel_out_file, found_articles)

                # Keep them in memory for potential scraping
                all_articles.extend(found_articles)

    else:
        logger.info("Skipping search logic. Loading existing articles from DB.")
        all_articles = load_articles_from_db(db_path, db_name)  
        # or load_articles_from_excel(excel_out_path, excel_out_file)
        # if you prefer Excel as your source

    # If scraping is enabled, scrape web pages / download PDFs
    if scrape_flag.lower() == "yes":
        
        scrape_engine_choice = config.get("scrape_engine_selection", "custom").lower()
        
        if scrape_engine_choice == "custom":
            from utils.scraper_custom_selenium import scrape_article
            logger.info("Using CUSTOM scrape engine.")
        else:
            from utils.scraper_zyte import scrape_article 
            logger.info("Using ZYTE scrape engine.")
            
        for article in all_articles:
            topic_for_article = article.get("search_query", "general")
            url = article["source_url"].lower()

            if url.endswith(".pdf"):
                article["date_retrieved"] = datetime.now().isoformat()
                store_article_pdf(markdown_out_path, article, topic_for_article, short_title_limit)
            else:
                content_md = scrape_article(article["source_url"], config)
                article["article_content"] = content_md
                article["date_retrieved"] = datetime.now().isoformat()
                store_article_markdown(markdown_out_path, article, topic_for_article, short_title_limit)

        # Update DB & Excel with final date_retrieved
        store_articles_in_db(db_path, db_name, all_articles)
        store_articles_in_excel(excel_out_path, excel_out_file, all_articles)
    else:
        logger.info("Scraping is disabled. No article content or PDF downloads will be performed.")

if __name__ == "__main__":
    main()