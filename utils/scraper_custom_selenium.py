import requests
import time
from utils.logger import logger
from markdownify import markdownify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

def scrape_article(url, max_scroll_attempts=3, scroll_pause=2, api_config=None):
    """
    Loads a webpage in a headless browser, handles 'read more' or infinite scroll,
    and returns the final HTML content.

    :param url: URL to scrape.
    :param max_scroll_attempts: Number of scroll cycles for infinite scroll.
    :param scroll_pause: Seconds to wait after each scroll for content to load.
    :return: Final HTML of the fully loaded page.
    """
    logger.debug(f"Using Selenium for dynamic content for: {url}")
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
            return markdownify(scrape_article(url))
    except Exception as e: 
        logger.exception(f"Error scraping article {url}: {e}")
        return ""