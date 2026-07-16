
import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

async def test_crawl():
    print("Starting test crawl...")
    browser_cfg = BrowserConfig(headless=True, verbose=True)
    run_cfg = CrawlerRunConfig(magic=True)
    
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun("https://example.com", config=run_cfg)
        if result.success:
            print("Successfully crawled example.com")
            print("Title:", result.markdown[:50])
        else:
            print("Failed to crawl:", result.error_message)

if __name__ == "__main__":
    asyncio.run(test_crawl())
