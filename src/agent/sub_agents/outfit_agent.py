import json
from pydantic_ai import Agent
from .base import get_azure_llm, Outfit
from src.database import SessionLocal
from src.models.clothing import ClothingItem


class WardrobeManager:
    """A class to manage wardrobe-related tools, ensuring they have user context."""

    def __init__(self, user_id: int):
        if not isinstance(user_id, int):
            raise TypeError("user_id must be an integer.")
        self.user_id = user_id
        self.db = SessionLocal()

    def __del__(self):
        if hasattr(self, 'db'):
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


def create_outfit_agent(user_id: int) -> Agent:
    """
    Creates an outfit recommendation agent for a specific user.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        Agent: Configured outfit recommendation agent
    """
    wardrobe_manager = WardrobeManager(user_id=user_id)
    
    return Agent(
        get_azure_llm(),
        output_type=Outfit,
        system_prompt="""You are a professional fashion stylist and outfit recommendation expert. Your job is to:

1. Use the `get_user_wardrobe` tool to access the user's clothing items
2. Create stylish and appropriate outfit combinations from their available items
3. Consider factors like color coordination, style compatibility, and occasion appropriateness
4. Provide clear reasoning for why the selected items work well together
5. If the wardrobe is empty or insufficient, inform the user and suggest what they might need

Always be encouraging and provide helpful fashion advice. Focus on creating outfits that are both stylish and practical.""",
        tools=[wardrobe_manager.get_user_wardrobe],
    )


async def recommend_outfit(user_id: int, request: str = "What should I wear today?") -> Outfit:
    """
    Get outfit recommendations for a user based on their wardrobe.
    
    Args:
        user_id: The ID of the user
        request: The specific outfit request (optional)
        
    Returns:
        Outfit: Structured outfit recommendation
    """
    try:
        agent = create_outfit_agent(user_id)
        result = await agent.run(request)
        return result.data
    except Exception as e:
        print(f"Error in recommend_outfit: {e}")
        # Return a helpful error message
        return Outfit(
            outfit_description="I'm sorry, I encountered an error while accessing your wardrobe.",
            items=[],
            reasoning="There was a technical issue. Please try again later or make sure your wardrobe has some items added."
        ) 