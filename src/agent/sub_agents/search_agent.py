import json
from typing import List
from pydantic_ai import Agent
from openai import AzureOpenAI
import os
from .base import get_azure_llm, ProductList, Product
from src.utils.google_search import google_search


async def search_web(query: str) -> str:
    """
    Searches the web using Google Search API and returns results with links.
    
    Args:
        query: Search query string
        
    Returns:
        JSON string containing search results with links
    """
    try:
        result = await google_search(query)
        data = json.loads(result)
        
        # Extract links from search results
        links = []
        if 'organic' in data:
            for item in data['organic']:
                if 'link' in item:
                    links.append({
                        'title': item.get('title', ''),
                        'link': item['link'],
                        'snippet': item.get('snippet', '')
                    })
        
        return json.dumps({'status': 'success', 'links': links, 'query': query})
    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)})


async def analyze_search_results_with_gpt4o(search_results: List[dict], original_query: str) -> ProductList:
    """
    Use Azure OpenAI GPT-4o with structured outputs to analyze search results 
    and extract product information without web scraping.
    
    Args:
        search_results: List of search result dictionaries with title, link, snippet
        original_query: The original search query
        
    Returns:
        ProductList: Structured list of products extracted from search results
    """
    try:
        # Configure Azure OpenAI client for structured outputs
        client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_API_BASE"],
            api_key=os.environ["AZURE_API_KEY"],
            api_version="2024-10-21"  # Version that supports structured outputs
        )
        
        # Prepare the search results text for analysis
        search_text = f"Original search query: {original_query}\n\n"
        search_text += "Search results:\n"
        
        for i, result in enumerate(search_results[:5], 1):  # Limit to top 5 results
            search_text += f"{i}. Title: {result.get('title', 'N/A')}\n"
            search_text += f"   Link: {result.get('link', 'N/A')}\n"
            search_text += f"   Description: {result.get('snippet', 'N/A')}\n\n"
        
        # Use structured outputs to get product information
        completion = client.beta.chat.completions.parse(
            model=os.environ["AZURE_DEPLOYMENT_NAME"],
            messages=[
                {
                    "role": "system", 
                    "content": """You are an expert product analyst. Your task is to analyze search results and extract product information including names, prices, descriptions, and links.

Instructions:
- Extract product information from the search results provided
- For each product, provide: name, price (with currency if available, or "Price not found"), description (concise, max 120 chars), and the direct link
- Only include actual products that are for sale
- If no clear products are found, return an empty list
- Focus on the most relevant products based on the search query
- Be accurate with product names and descriptions"""
                },
                {
                    "role": "user",
                    "content": f"Please analyze these search results and extract product information:\n\n{search_text}"
                }
            ],
            response_format=ProductList,
            max_tokens=4096,
            temperature=0.1
        )
        
        # Extract the structured response
        if completion.choices[0].message.parsed:
            return completion.choices[0].message.parsed
        else:
            print("No parsed response received")
            return ProductList(products=[])
            
    except Exception as e:
        print(f"Error in analyze_search_results_with_gpt4o: {e}")
        return ProductList(products=[])


async def find_products_online(query: str) -> str:
    """
    A comprehensive tool to find products online using search results analysis with GPT-4o.
    This approach is much faster and more reliable than web scraping.

    Args:
        query: The user's search query for a product.

    Returns:
        JSON string with product information or error message.
    """
    print(f"Starting product search for query: {query}")
    try:
        # 1. Search for links using Google Search API
        search_results_json = await search_web(query)
        search_results = json.loads(search_results_json)

        if search_results.get("status") != "success" or not search_results.get("links"):
            return json.dumps({
                "status": "error", 
                "message": "Could not find any relevant links for the query."
            })

        # 2. Use GPT-4o with structured outputs to analyze search results
        product_list = await analyze_search_results_with_gpt4o(
            search_results["links"], 
            query
        )
        
        if product_list.products:
            return json.dumps({
                "status": "success", 
                "products": [product.model_dump() for product in product_list.products],
                "query": query
            })
        else:
            return json.dumps({
                "status": "success", 
                "products": [],
                "message": "No products found in search results"
            })

    except Exception as e:
        print(f"An error occurred in find_products_online: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"An error occurred while searching for products: {e}"
        })


# Create the search agent
search_agent = Agent(
    get_azure_llm(),
    output_type=ProductList,
    system_prompt="""You are a specialized product search agent using advanced AI analysis. Your job is to:

1. Use the `find_products_online` tool to search for products based on user queries
2. The tool uses GPT-4o with structured outputs to analyze search results and extract product information
3. Return a structured ProductList with accurate product details including name, price, description, and link
4. Ensure all product information is properly formatted and relevant to the user's search

This approach is much faster and more reliable than traditional web scraping.""",
    tools=[find_products_online],
)


async def search_products(query: str) -> ProductList:
    """
    Search for products online using AI-powered search result analysis.
    
    Args:
        query: The search query for products
        
    Returns:
        ProductList: Structured list of found products
    """
    try:
        result = await search_agent.run(query)
        return result.data
    except Exception as e:
        print(f"Error in search_products: {e}")
        # Return empty result on error
        return ProductList(products=[]) 