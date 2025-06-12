import asyncio
from crawl4ai import AsyncWebCrawler

async def scrap_website(url: str):
    """
    Scrapes a website and returns the result object with markdown content.
    
    Args:
        url: The URL to scrape
        
    Returns:
        Result object from the crawler with markdown content
    """
    try:
        # Create an instance of AsyncWebCrawler
        async with AsyncWebCrawler() as crawler:
            # Run the crawler on a URL
            result = await crawler.arun(url=url)
            return result
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None