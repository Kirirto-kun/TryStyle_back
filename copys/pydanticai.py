import asyncio
import json
import os
from typing import List, Union

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider

from src.database import SessionLocal
from src.models.clothing import ClothingItem
from src.utils.google_search import google_search, google_lens_search
from src.utils.scrap_website import scrap_website

# Load environment variables from .env file
load_dotenv()


# Pydantic Models for Structured Output
class Product(BaseModel):
    name: str = Field(..., description="Product/service name")
    price: str = Field(
        ...,
        description='Price with currency symbol if present, or "Price not found" if absent',
    )
    description: str = Field(
        ..., description="Concise 1-2 sentence description (max 120 chars)"
    )
    link: str = Field(..., description="Direct link to the product page")


class ProductList(BaseModel):
    products: List[Product] = Field(..., description="A list of products found.")


class Outfit(BaseModel):
    outfit_description: str = Field(
        ..., description="A friendly description of the outfit."
    )
    items: List[dict] = Field(
        ...,
        description="List of clothing items in the outfit, with name, category and image_url.",
    )
    reasoning: str = Field(
        ..., description="A brief explanation of why these items work together."
    )


class GeneralResponse(BaseModel):
    response: str = Field(
        ..., description="A helpful and friendly response to a general user query."
    )


# Combined Output Model
class AgentResponse(BaseModel):
    """The final response object to the user."""

    result: Union[ProductList, Outfit, GeneralResponse] = Field(
        ..., description="The result of the agent's work, can be a list of products, an outfit, or a general response."
    )


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


async def scrape_websites(links_json: str) -> str:
    """
    Scrapes multiple websites and returns their markdown content.
    
    Args:
        links_json: JSON string containing list of links to scrape
        
    Returns:
        JSON string containing scraped content for each URL
    """
    try:
        links_data = json.loads(links_json)
        if 'links' not in links_data:
            return json.dumps({'status': 'error', 'message': 'Invalid links format'})
        
        scraped_content = []
        for link_info in links_data['links'][:5]:  # Limit to 5 links to avoid timeouts
            try:
                url = link_info['link']
                result = await scrap_website(url)
                if result and hasattr(result, 'markdown'):
                    scraped_content.append({
                        'url': url,
                        'title': link_info.get('title', ''),
                        'content': result.markdown[:5000],  # Limit content size
                        'status': 'success'
                    })
                else:
                    scraped_content.append({
                        'url': url,
                        'title': link_info.get('title', ''),
                        'content': '',
                        'status': 'failed',
                        'error': 'No markdown content returned'
                    })
            except Exception as e:
                scraped_content.append({
                    'url': link_info['link'],
                    'title': link_info.get('title', ''),
                    'content': '',
                    'status': 'failed',
                    'error': str(e)
                })
        
        return json.dumps({'status': 'success', 'scraped_data': scraped_content})
    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)})


async def find_products_online(query: str) -> str:
    """
    A comprehensive tool to find products online. It searches the web,
    scrapes the top 3 relevant pages, and returns their content for extraction.
    Use this for any requests related to finding or searching for items/products online.

    Args:
        query: The user's search query for a product.

    Returns:
        The combined markdown content from the scraped web pages.
    """
    print(f"Starting product search for query: {query}")
    try:
        # 1. Search for links
        search_results_json = await search_web(query)
        search_results = json.loads(search_results_json)

        if search_results.get("status") != "success" or not search_results.get("links"):
            return "Could not find any relevant links for the query."

        # 2. Scrape the top 3 links
        links_to_scrape = {"links": search_results["links"][:3]}
        scraped_content_json = await scrape_websites(json.dumps(links_to_scrape))
        scraped_content = json.loads(scraped_content_json)

        if (
            scraped_content.get("status") != "success"
            or not scraped_content.get("scraped_data")
        ):
            return "Could not scrape content from the found links."

        # 3. Combine content for the LLM to process
        all_content = ""
        for item in scraped_content["scraped_data"]:
            if item["status"] == "success" and item["content"]:
                all_content += (
                    f"Source URL: {item['url']}\n"
                    f"Page Content:\n{item['content']}\n\n---\n\n"
                )

        if not all_content:
            return "The content of the websites was empty or could not be read."

        return all_content
    except Exception as e:
        print(f"An error occurred in find_products_online: {e}")
        return f"An error occurred while searching for products: {e}"


class WardrobeManager:
    """A class to manage wardrobe-related tools, ensuring they have user context."""

    def __init__(self, user_id: int):
        if not isinstance(user_id, int):
            raise TypeError("user_id must be an integer.")
        self.user_id = user_id
        self.db = SessionLocal()

    def __del__(self):
        self.db.close()

    def get_user_wardrobe(self) -> str:
        """
        Retrieves all clothing items from the authenticated user's wardrobe.
        Use this tool when the user asks for an outfit recommendation or wants to
        know what is in their wardrobe.
        """
        print(f"Fetching wardrobe for user_id: {self.user_id}")
        try:
            items = (
                self.db.query(ClothingItem)
                .filter(ClothingItem.user_id == self.user_id)
                .all()
            )

            if not items:
                return json.dumps(
                    {
                        "status": "success",
                        "wardrobe": [],
                        "message": "The user's wardrobe is empty. You should inform the user about this.",
                    }
                )

            wardrobe = [
                {
                    "name": item.name,
                    "image_url": item.image_url,
                    "category": item.category,
                    "features": item.features,
                }
                for item in items
            ]
            return json.dumps({"status": "success", "wardrobe": wardrobe})
        except Exception as e:
            print(f"An error occurred in get_user_wardrobe: {e}")
            return json.dumps(
                {"status": "error", "message": "An error occurred while fetching the wardrobe."}
            )


async def process_user_request(message: str, user_id: int) -> str:
    """
    Processes a user's request using a PydanticAI-powered agent.

    This function routes the user's request to the appropriate tool:
    - `find_products_online` for web searches.
    - `get_user_wardrobe` for outfit recommendations.
    - Responds to general queries directly.

    Args:
        message: The user's message/request.
        user_id: The ID of the authenticated user.

    Returns:
        A JSON string containing the agent's final response.
    """
    try:
        # 1. Configure the LLM for Azure OpenAI
        llm = OpenAIModel(
            model_name=os.environ["AZURE_DEPLOYMENT_NAME"],
            provider=AzureProvider(
                azure_endpoint=os.environ["AZURE_API_BASE"],
                api_version=os.environ["AZURE_API_VERSION"],
                api_key=os.environ["AZURE_API_KEY"],
            ),
        )

        # 2. Instantiate tools with necessary context
        wardrobe_manager = WardrobeManager(user_id=user_id)
        tools = [find_products_online, wardrobe_manager.get_user_wardrobe]

        # 3. Create the PydanticAI instance
        agent = Agent(
            llm,
            system_prompt="""You are a multi-talented assistant. Your capabilities are:
            1.  **Web Product Search**: If the user asks to find an item, product, or any information online, use the `find_products_online` tool. Then, from the returned text which contains website content, extract the product details into the `ProductList` model.
            2.  **Outfit Recommendation**: If the user asks for an outfit, to get dressed, or something about their clothes, use the `get_user_wardrobe` tool. Based on the items, create a stylish outfit and format it using the `Outfit` model. If the wardrobe is empty, inform the user.
            3.  **General Conversation**: For any other questions or simple chat, respond politely and helpfully, formatting your answer in the `GeneralResponse` model.

            Analyze the user's request and choose the appropriate tool and output format.
            """,
            result_type=AgentResponse,
            tools=tools,
            # chat_history= # Potentially add chat history here
        )

        # 4. Run the agent
        response = await agent.run(message)
        
        # 5. Format and return the response
        return response.data.model_dump_json(indent=2)

    except Exception as e:
        print(f"An error occurred while processing the request: {e}")
        return json.dumps({"error": f"An error occurred: {str(e)}"}, indent=2)

# Example usage (for testing)
# async def main():
#     print("Processing request...")
#     # Test case 1: Product search
#     response_search = await process_user_request("Can you find me a black t-shirt?", user_id=1)
#     print("\n--- Product Search Response ---")
#     print(response_search)

#     # Test case 2: Outfit recommendation (assuming user 1 has items in the DB)
#     # response_outfit = await process_user_request("What should I wear today?", user_id=1)
#     # print("\n--- Outfit Recommendation Response ---")
#     # print(response_outfit)

#     # Test case 3: General question
#     # response_general = await process_user_request("What is PydanticAI?", user_id=1)
#     # print("\n--- General Question Response ---")
#     # print(response_general)

# if __name__ == "__main__":
#     asyncio.run(main())