import json
from pydantic_ai import Agent, ModelRetry
from typing import List
from .base import get_azure_llm, Outfit, OutfitItem
from src.database import SessionLocal
from src.models.clothing import ClothingItem
from pydantic_ai.messages import ModelMessage


# Cache for outfit agents by user_id
_outfit_agents_cache = {}


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
        Returns structured data for enhanced AI processing.
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
                        "total_items": 0,
                        "message": "The user's wardrobe is empty. You should inform the user about this and suggest adding clothing items.",
                    }
                )

            # Enhanced wardrobe data with categorization
            wardrobe = []
            categories = {}
            
            for item in items:
                item_data = {
                    "name": item.name,
                    "image_url": item.image_url,
                    "category": item.category,
                    "features": item.features,
                }
                wardrobe.append(item_data)
                
                # Count by category for better outfit planning
                categories[item.category] = categories.get(item.category, 0) + 1
            
            return json.dumps({
                "status": "success", 
                "wardrobe": wardrobe,
                "total_items": len(wardrobe),
                "categories": categories,
                "message": f"Found {len(wardrobe)} items across {len(categories)} categories."
            })
            
        except Exception as e:
            print(f"An error occurred in get_user_wardrobe: {e}")
            return json.dumps(
                {"status": "error", "message": "An error occurred while fetching the wardrobe."}
            )


def create_outfit_agent(user_id: int) -> Agent:
    """
    Creates or returns a cached outfit recommendation agent for a specific user.
    Enhanced with strict structured output validation and conversation context awareness.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        Agent: Configured outfit recommendation agent (cached per user) with context awareness
    """
    global _outfit_agents_cache
    
    # Check if we already have an agent for this user
    if user_id in _outfit_agents_cache:
        return _outfit_agents_cache[user_id]
    
    # Create new agent for this user
    wardrobe_manager = WardrobeManager(user_id=user_id)
    
    agent = Agent(
        get_azure_llm(),
        output_type=Outfit,
        system_prompt="""You are a professional fashion stylist and outfit recommendation expert with conversation context awareness and strict output requirements.

CONVERSATION CONTEXT AWARENESS:
- You have access to conversation history to understand user preferences, feedback, and style evolution
- If user provides feedback on previous outfit recommendations, learn from it and adjust
- Remember user preferences mentioned in previous messages (occasions, colors, styles, comfort level, etc.)
- For follow-up outfit requests, consider what the user liked/disliked about previous recommendations
- Understand refinements like "something more formal", "different colors", "more comfortable", "less accessories", etc.
- Track user's style journey and preferences over time

STRUCTURED OUTPUT REQUIREMENTS:
- You MUST return a valid Outfit object with ALL required fields
- outfit_description: 20-300 characters, friendly and detailed style description
- items: Array of OutfitItem objects (0-8 max), each with name, category, image_url
- reasoning: 15-200 characters explaining why items work together
- occasion: Must be one of: casual, formal, business, evening, sport, weekend, date, work

CONTEXTUAL OUTFIT CREATION PROCESS:
1. Use get_user_wardrobe tool to access user's clothing items
2. Analyze conversation history for style preferences and feedback
3. Consider previous outfit recommendations and user reactions
4. Create outfits that incorporate learned preferences and address previous feedback
5. Balance user's stated preferences with styling best practices
6. Provide clear styling rationale that references context when relevant

PREFERENCE LEARNING:
- Color preferences: Track which colors user likes/dislikes
- Style preferences: Note if user prefers casual vs formal, loose vs fitted, etc.
- Occasion feedback: Learn user's specific needs for different events
- Comfort preferences: Remember if user values comfort over style or vice versa
- Accessory preferences: Note if user likes minimal or statement accessories

VALIDATION RULES:
- If wardrobe is empty: return empty items array with helpful message
- Only use items that actually exist in the user's wardrobe
- Ensure outfit items have valid categories: Tops, Bottoms, Outerwear, Footwear, Accessories, Dresses, Activewear
- All text fields must meet length requirements (no empty or too long content)
- Each outfit should be practical and stylistically coherent
- Consider conversation context when selecting items and providing reasoning

CONTEXTUAL EXAMPLES:
- If user said previous outfit was "too formal", suggest more casual alternatives
- If user mentioned liking certain colors, incorporate them when appropriate
- If user gave feedback about comfort, prioritize comfortable pieces
- If user has a specific event coming up, tailor recommendations accordingly

QUALITY STANDARDS:
- Prioritize wearability and style compatibility
- Consider color coordination and seasonal appropriateness
- Provide constructive fashion advice with contextual reasoning
- Handle edge cases gracefully (empty wardrobe, limited items)
- Build upon previous styling successes

ERROR HANDLING:
- Always return valid Outfit structure even with empty wardrobe
- Provide helpful suggestions when items are limited
- Use appropriate occasion classification
- Reference conversation context in reasoning when relevant""",
        tools=[wardrobe_manager.get_user_wardrobe],
        retries=5  # Increased retries for better reliability
    )

    # Add output validator for strict validation
    @agent.output_validator
    async def validate_outfit_output(output: Outfit) -> Outfit:
        """Validate and enhance outfit output quality."""
        if not isinstance(output, Outfit):
            raise ModelRetry("Output must be a valid Outfit object")
        
        # Validate text field lengths
        if len(output.outfit_description.strip()) < 20:
            raise ModelRetry("Outfit description must be at least 20 characters")
        
        if len(output.reasoning.strip()) < 15:
            raise ModelRetry("Reasoning must be at least 15 characters")
        
        # Validate items structure
        if len(output.items) > 8:
            raise ModelRetry("Maximum 8 items allowed per outfit")
        
        # Validate each item
        validated_items = []
        for item in output.items:
            if not isinstance(item, OutfitItem):
                continue
            
            # Ensure item name is not empty
            if not item.name or not item.name.strip():
                continue
                
            validated_items.append(item)
        
        # Update with validated items
        output.items = validated_items
        
        # Ensure occasion is set
        if not output.occasion:
            output.occasion = "casual"
        
        return output
    
    # Cache the agent for this user
    _outfit_agents_cache[user_id] = agent
    
    return agent


def clear_outfit_agent_cache(user_id: int = None):
    """
    Clear outfit agent cache for a specific user or all users.
    Useful when user's wardrobe changes significantly.
    
    Args:
        user_id: Specific user ID to clear cache for, or None to clear all
    """
    global _outfit_agents_cache
    
    if user_id is not None:
        if user_id in _outfit_agents_cache:
            del _outfit_agents_cache[user_id]
    else:
        _outfit_agents_cache.clear()


async def recommend_outfit(user_id: int, request: str = "What should I wear today?", message_history: List[ModelMessage] = None) -> Outfit:
    """
    Get outfit recommendations for a user based on their wardrobe with conversation context awareness.
    Now understands conversation history for better contextual outfit recommendations!
    
    Args:
        user_id: The ID of the user
        request: The specific outfit request (optional)
        message_history: Optional conversation history for context and preference learning
        
    Returns:
        Outfit: Strictly validated outfit recommendation with context awareness
    """
    try:
        agent = create_outfit_agent(user_id)
        result = await agent.run(
            request,
            message_history=message_history
        )
        return result.data
    except Exception as e:
        print(f"Error in recommend_outfit: {e}")
        # Return a helpful error message in the correct structured format
        return Outfit(
            outfit_description="I'm sorry, I encountered an error while accessing your wardrobe. Please try again or ensure your wardrobe has clothing items added.",
            items=[],
            reasoning="Technical issue occurred during outfit generation. Your wardrobe data may be temporarily unavailable.",
            occasion="casual"
        ) 