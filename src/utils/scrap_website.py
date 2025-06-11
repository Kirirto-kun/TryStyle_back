import asyncio
from crawl4ai import AsyncWebCrawler

async def scrap_website(url: str):
    # Create an instance of AsyncWebCrawler
    async with AsyncWebCrawler() as crawler:
        # Run the crawler on a URL
        result = await crawler.arun(url=url)

        # Print the extracted content
        print(result.markdown)