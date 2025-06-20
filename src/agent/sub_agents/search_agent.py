import json
import asyncio
from typing import List
from pydantic_ai import Agent, ModelRetry, RunContext
from .base import get_azure_llm, ProductList, Product, MessageHistory
from src.utils.google_search import google_search
from pydantic_ai.messages import ModelMessage
from dataclasses import dataclass


# A new agent instance dedicated to extracting product info from a single URL.
# This approach encapsulates the extraction logic cleanly.
url_extractor_agent = Agent(
    model=get_azure_llm(),
    output_type=ProductList,
    system_prompt="""You are an expert web page analyst specializing in e-commerce. Your task is to analyze the content of a given URL to find products matching a user's query.

INSTRUCTIONS:
1.  Carefully examine the content of the provided URL. The user's query and the URL will be given in the prompt.
2.  Based on the user's query, identify any and all products that are a good match.
3.  For each matching product, extract its name, price, a brief description, and set the link to the URL you were given.
4.  If the page is a list of multiple products (e.g., a category or search results page), extract all products that match the query.
5.  If the page is a single product page, extract that product's information if it matches the query.
6.  Return your findings as a `ProductList` object. The `search_query` should be the user's original query.
7.  If no matching products are found, or if the page is irrelevant (e.g., an article, a blog post), return a `ProductList` with an empty `products` list.
8.  The `price` field must be a string containing the price exactly as seen on the page (e.g., "₽1,500.00", "$29.99", "Price not available").
""",
    retries=2,
    # Adding an output validator for robustness
    output_validator=lambda output: output if isinstance(output, ProductList) else ModelRetry("Output must be a ProductList")
)

async def extract_products_from_url(url: str, query: str) -> List[Product]:
    """Analyzes a single URL using a powerful LLM to extract product information."""
    print(f"   Analyzing page with LLM: {url}")
    try:
        prompt = f"User Query: \"{query}\"\n\nPlease analyze this URL and extract all matching products based on my query: {url}"
        result = await url_extractor_agent.run(prompt)
        
        products = result.data.products
        if products:
            print(f"      ✅ Found {len(products)} product(s) on {url}")
            # Ensure the link and query are set correctly for each product
            for p in products:
                p.link = url
            return products
        else:
            print(f"      ❌ No matching products found on {url}")
            return []
    except Exception as e:
        print(f"      ❗️ Error analyzing URL {url}: {e}")
        return []


async def intelligent_product_search(query: str) -> ProductList:
    """
    Performs an intelligent, multi-stage search for products.
    This is the main entry point for all product searches.

    Workflow:
    1.  Uses Google Search to find relevant URLs.
    2.  Uses a specialized AI agent to analyze each URL concurrently.
    3.  The AI agent extracts product details if the page content matches the user query.
    4.  Returns a curated list of verified products.

    Args:
        query: The user's full, original search query.
    """
    print(f"🔍 Starting intelligent search for: {query}")
    try:
        # Этап 1: Поиск в Google
        print("🔎 Stage 1: Performing Google search...")
        search_results_json = await google_search(query)
        search_results = json.loads(search_results_json).get('organic', [])
        
        urls = [
            result['link'] for result in search_results 
            if 'link' in result and not any(x in result['link'] for x in ['.gov', '.xml', 'pinterest.com', 'youtube.com'])
        ]
        print(f"   - Found {len(urls)} potential URLs.")

        if not urls:
            return ProductList(products=[], search_query=query, total_found=0)

        # Этап 2: Параллельный анализ страниц с помощью LLM
        # We limit analysis to the top 8 results to balance speed and coverage.
        print(f"🤖 Stage 2: Analyzing top {min(len(urls), 8)} URLs concurrently...")
        tasks = [extract_products_from_url(url, query) for url in urls[:8]]
        
        results_from_urls = await asyncio.gather(*tasks)
        
        # Flatten the list of lists and remove duplicates
        all_products = []
        seen_products = set()
        for product_list in results_from_urls:
            for product in product_list:
                # Simple deduplication based on product name and link
                product_identifier = (product.name.strip().lower(), product.link)
                if product_identifier not in seen_products:
                    all_products.append(product)
                    seen_products.add(product_identifier)

        print(f"✅ Stage 3: Found {len(all_products)} unique matching products.")
        
        return ProductList(
            products=all_products[:20],  # Return up to 20 products
            search_query=query,
            total_found=len(all_products)
        )
        
    except Exception as e:
        print(f"❌ Error in intelligent_product_search: {e}")
        return ProductList(products=[], search_query=query, total_found=0)


# Cached search agent instance
_search_agent_instance = None

def get_search_agent() -> Agent:
    """
    Returns a search agent designed to delegate tasks to the `intelligent_product_search` tool.
    This agent's sole purpose is to orchestrate the search by calling its main tool.
    """
    global _search_agent_instance
    
    if _search_agent_instance is None:
        _search_agent_instance = Agent(
            get_azure_llm(),
            output_type=ProductList,
            system_prompt="""You are a search orchestrator. Your only job is to call the `intelligent_product_search` tool to find products for the user.
Use the user's original, unmodified query as the input for the tool. Do not add, change, or remove anything from the user's query.
""",
            tools=[intelligent_product_search],
            retries=2
        )
    
    return _search_agent_instance 