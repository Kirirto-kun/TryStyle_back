import httpx
from bs4 import BeautifulSoup
from typing import Optional

async def scrape_page_content(url: str) -> Optional[str]:
    """
    Asynchronously scrapes the textual content of a web page, cleaning it for AI analysis.

    Args:
        url: The URL of the web page to scrape.

    Returns:
        A string containing the cleaned text content of the page, or None if scraping fails.
        The content is limited to the first 8000 characters to optimize for LLM processing.
    """
    try:
        # Standard headers to mimic a web browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Connection': 'keep-alive',
        }
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            response = await client.get(url, headers=headers)
            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()
        
        # Parse the HTML content of the page
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements as they don't contain useful product info
        for script_or_style in soup(['script', 'style', 'nav', 'footer', 'header']):
            script_or_style.decompose()
            
        # Extract text, replace multiple whitespaces with a single space, and join lines
        text = ' '.join(soup.stripped_strings)
        
        # Limit content size to avoid overwhelming the language model
        return text[:8000]
        
    except httpx.HTTPStatusError as e:
        print(f"HTTP error scraping {url}: {e.response.status_code}")
        return None
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None 