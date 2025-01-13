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
        store_article_pdf
)
from markdownify import markdownify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

def handle_dynamic_content(url, max_scroll_attempts=3, scroll_pause=2):
    """
    Loads a webpage in a headless browser, handles 'read more' or infinite scroll,
    and returns the final HTML content.

    :param url: URL to scrape.
    :param max_scroll_attempts: Number of scroll cycles for infinite scroll.
    :param scroll_pause: Seconds to wait after each scroll for content to load.
    :return: Final HTML of the fully loaded page.
    """
    logger.debug(f"Handling dynamic content for: {url}")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = None

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        time.sleep(scroll_pause)  # Initial wait for page load

        # Attempt to click any 'read more' buttons that might reveal more text
        try:
            # Example: searching by CSS or text. Adjust as needed for site structure.
            read_more_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Read More')]")
            for btn in read_more_buttons:
                btn.click()
                time.sleep(scroll_pause)
        except NoSuchElementException:
            logger.debug("No 'read more' buttons found.")

        # Attempt infinite scroll if the page uses lazy-loaded content
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(max_scroll_attempts):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        final_html = driver.page_source
        return final_html

    except Exception as e:
        logger.exception(f"Error handling dynamic content: {e}")
        return ""
    finally:
        if driver:
            driver.quit()

def scrape_article(url):
    logger.debug(f"Scraping article: {url}")
    try:
        response = requests.get(url, timeout=10)
        if response.ok:
            return markdownify(response.text)
        else:
            logger.warning("Non-200 response. Attempting dynamic content load.")
            return markdownify(handle_dynamic_content(url))
    except Exception as e: 
        logger.exception(f"Error scraping article {url}: {e}")
        return ""

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
        logger.debug(f"Applying dateRestrict: {date_restrict_value}")

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

    scrape_flag = config.get("scrape_articles", "yes")
    deduplicate_flag = config.get("de_duplicate_articles", "off")

    markdown_settings = config.get("markdown_settings", {})
    short_title_limit = markdown_settings.get("short_title_limit", 15)

    db_path = config["db_storage"]["path"]
    db_name = config["db_storage"]["name"]
    excel_out_path = config["output_excel"]["path"]
    excel_out_file = config["output_excel"]["file_name"]
    markdown_out_path = config["output_markdown"]["path"]

    topic_config = config.get("topics", {})
    domains_config = config.get("domains", {})

    # Load topics
    topics_excel = os.path.join(topic_config["location"], topic_config["excel_file_name"])
    topics_df = pd.read_excel(topics_excel, sheet_name=topic_config["sheet_name"])
    topics_list = topics_df[topic_config["column_name"]].dropna().tolist()

    # Load domains
    domains_excel = os.path.join(domains_config["location"], domains_config["excel_file_name"])
    domains_df = pd.read_excel(domains_excel, sheet_name=domains_config["sheet_name"])
    domains_records = domains_df.to_dict("records")

    all_articles = []

    # Initialize daily query counter
    daily_count = 0

    # Perform searches
    for topic in topics_list:
        # If we've already reached daily limit, stop
        if daily_count >= max_qpd:
            logger.info("Max daily queries reached. Skipping further topics.")
            break

        for domain_row in domains_records:
            if daily_count >= max_qpd:
                logger.info("Max daily queries reached. Skipping further domains.")
                break

            domain_value = domain_row[domains_config["columns"]["domain"]]
            max_articles = domain_row[domains_config["columns"]["max_articles"]]

            # Increment daily_count because each call to search_articles is a new query
            if daily_count < max_qpd:
                found_articles = search_articles(
                    selected_engine_config,
                    topic,
                    domain_value,
                    max_articles,
                    max_qpm
                )
                daily_count += 1
            else:
                logger.info("Max daily queries reached mid-process. Skipping.")
                break

            if not found_articles:
                logger.warning(f"No results for topic='{topic}' domain='{domain_value}'.")

            all_articles.extend(found_articles)

    # Deduplicate if needed
    if deduplicate_flag.lower() == "on":
        unique_urls = set()
        deduped_articles = []
        for article in all_articles:
            if article["source_url"] not in unique_urls:
                article["suspected_duplicate"] = "no"
                unique_urls.add(article["source_url"])
                deduped_articles.append(article)
            else:
                article["suspected_duplicate"] = "yes"
                deduped_articles.append(article)
        all_articles = deduped_articles
    else:
        seen = set()
        for article in all_articles:
            if article["source_url"] in seen:
                article["suspected_duplicate"] = "yes"
            else:
                article["suspected_duplicate"] = "no"
                seen.add(article["source_url"])

    # Store search results (no article content yet)
    store_articles_in_db(db_path, db_name, all_articles)
    store_articles_in_excel(excel_out_path, excel_out_file, all_articles)

    # If scraping is enabled, scrape web pages / download PDFs
    if scrape_flag.lower() == "yes":
        for article in all_articles:
            topic_for_article = article.get("search_query", "general")
            url = article["source_url"].lower()

            if url.endswith(".pdf"):
                article["date_retrieved"] = datetime.now().isoformat()
                store_article_pdf(markdown_out_path, article, topic_for_article, short_title_limit)
            else:
                content_md = scrape_article(article["source_url"])
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