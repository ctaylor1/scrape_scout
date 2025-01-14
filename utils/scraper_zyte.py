import requests
from base64 import b64decode
from markdownify import markdownify
from utils.json_to_markdown import json_to_markdown
from utils.logger import logger

def scrape_article(url,api_config):
    """
    Scrapes article using Zyte API for dynamic content.
    Fetches api_url and api_key from the provided engine_config dict.
    """
    # Access zyte's specific configuration
    zyte_config = api_config.get('scrape_engines', {}).get('zyte', {})

    # Fetch zyte API variables
    zyte_api_url = zyte_config.get('api_url')
    zyte_api_key = zyte_config.get('api_key')
    
    logger.debug(f"Using Zyte for dynamic content: {url}")
    
    try:
        payload = {
            "url": url,
            "httpResponseBody": True,
            "article": True,
            "articleOptions": {"extractFrom": "httpResponseBody"},
        }

        # Make the POST request, passing the api_key as the username in basic auth
        api_response = requests.post(
            zyte_api_url,
            auth=(zyte_api_key, ""),  
            json=payload,
            timeout=20
        )
        api_response.raise_for_status()

        resp_json = api_response.json()

        # Decode the base64-encoded HTML if present
        http_response_body_base64 = resp_json.get("httpResponseBody")
        if http_response_body_base64:
            http_response_body = b64decode(http_response_body_base64)
            with open("http_response_body.html", "wb") as fp:
                fp.write(http_response_body)
            html_str = http_response_body.decode("utf-8", errors="replace")
        else:
            logger.warning("No 'httpResponseBody' key in Zyte response.")
            html_str = ""

        # Log article info if needed
        article = resp_json.get("article", {})
        logger.debug(f"Zyte article JSON Response: {article}")

        # Convert entire JSON to a structured Markdown:
        md_output = json_to_markdown(article)  # or resp_json?
        return md_output

    except Exception as e:
        logger.exception(f"Error scraping article with Zyte for {url}: {e}")
        return ""

