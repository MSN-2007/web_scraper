import json
import os
from typing import List, Set, Tuple, Dict, Any, Optional

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    LLMExtractionStrategy,
)

from models.venue import Venue
from utils.data_utils import is_complete_venue, is_duplicate_venue


def get_browser_config() -> BrowserConfig:
    """
    Returns the browser configuration for the crawler.

    Returns:
        BrowserConfig: The configuration settings for the browser.
    """
    # https://docs.crawl4ai.com/core/browser-crawler-config/
    return BrowserConfig(
        browser_type="chromium",  # Type of browser to simulate
        headless=True,  # Whether to run in headless mode (no GUI)
        verbose=True,  # Enable verbose logging
    )


def get_llm_strategy(api_key: str, schema_config: Dict[str, Any], schema_model: Any) -> LLMExtractionStrategy:
    """
    Returns the configuration for the language model extraction strategy.
    
    Args:
        api_key (str): The Gemini API key.
        schema_config (Dict[str, Any]): The schema configuration dictionary.
        schema_model (Any): The dynamically generated Pydantic model.

    Returns:
        LLMExtractionStrategy: The settings for how to extract data using LLM.
    """
    # Build dynamic LLM prompt instruction utilizing simple-language descriptions
    active_field_descriptions = []
    for field_name, info in schema_config.items():
        if info.get("active", False):
            desc = info.get("description", field_name)
            active_field_descriptions.append(f"'{field_name}' ({desc})")

    instruction = (
        "Extract all item objects with the following properties from the content:\n"
        + "\n".join([f"- {desc}" for desc in active_field_descriptions])
        + "\n\nCRITICAL: If any of the requested properties are not present or not available in the content, set their value strictly to null."
    )

    # https://docs.crawl4ai.com/api/strategies/#llmextractionstrategy
    return LLMExtractionStrategy(
        provider="gemini/gemini-flash-latest",  # Name of the LLM provider
        api_token=api_key or os.getenv("GEMINI_API_KEY"),  # API token for authentication
        schema=schema_model.model_json_schema(),  # Dynamic JSON schema of the data model
        extraction_type="block",  # Type of extraction to perform
        instruction=instruction,  # Dynamic instructions for the LLM
        input_format="markdown",  # Format of the input content
        verbose=True,  # Enable verbose logging
    )


async def check_no_results(
    crawler: AsyncWebCrawler,
    url: str,
    session_id: str,
) -> bool:
    """
    Checks if the "No Results Found" message is present on the page.

    Args:
        crawler (AsyncWebCrawler): The web crawler instance.
        url (str): Target webpage URL.
        session_id (str): The session identifier.

    Returns:
        bool: True if "No Results Found" message is found, False otherwise.
    """
    # Fetch the page without any CSS selector or extraction strategy
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            magic=True,
        ),
    )

    if result.success:
        if "No Results Found" in result.cleaned_html:
            return True
    else:
        print(
            f"Error fetching page for 'No Results Found' check: {result.error_message}"
        )

    return False


async def fetch_and_process_page(
    crawler: AsyncWebCrawler,
    page_number: int,
    base_url: str,
    css_selector: str,
    llm_strategy: LLMExtractionStrategy,
    session_id: str,
    required_keys: List[str],
    seen_names: Set[str],
) -> Tuple[List[dict], bool]:
    """
    Fetches and processes a single page of data using LLM extraction strategy.

    Args:
        crawler (AsyncWebCrawler): The web crawler instance.
        page_number (int): The page number to fetch.
        base_url (str): The base URL of the website.
        css_selector (str): The CSS selector to target the content.
        llm_strategy (LLMExtractionStrategy): The LLM extraction strategy.
        session_id (str): The session identifier.
        required_keys (List[str]): List of required keys in the data.
        seen_names (Set[str]): Set of names that have already been seen.

    Returns:
        Tuple[List[dict], bool]:
            - List[dict]: A list of processed items from the page.
            - bool: A flag indicating if the "No Results Found" message was encountered.
    """
    url = f"{base_url}?page={page_number}"
    print(f"Loading page {page_number}...")

    # Check if "No Results Found" message is present
    no_results = await check_no_results(crawler, url, session_id)
    if no_results:
        return [], True  # No more results, signal to stop crawling

    # Fetch page content with the extraction strategy
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,  # Do not use cached data
            extraction_strategy=llm_strategy,  # Strategy for data extraction
            css_selector=css_selector,  # Target specific content on the page
            magic=True,
        ),
    )

    if not (result.success and result.extracted_content):
        print(f"Error fetching page {page_number}: {result.error_message}")
        return [], False

    # Parse extracted content
    extracted_data = json.loads(result.extracted_content)
    if not extracted_data:
        print(f"No results found on page {page_number}.")
        return [], False

    print("Extracted data:", extracted_data)

    # Process extracted items
    complete_items = []
    for item in extracted_data:
        print("Processing item:", item)

        # Ignore the 'error' key if it's False
        if item.get("error") is False:
            item.pop("error", None)

        if not is_complete_venue(item, required_keys):
            print(f"Skipping incomplete item: {item}")
            continue

        if is_duplicate_venue(item["name"], seen_names):
            print(f"Duplicate item '{item['name']}' found. Skipping.")
            continue

        # Add item to the list
        seen_names.add(item["name"])
        complete_items.append(item)

    if not complete_items:
        print(f"No complete items found on page {page_number}.")
        return [], False

    print(f"Extracted {len(complete_items)} complete items from page {page_number}.")
    return complete_items, False
