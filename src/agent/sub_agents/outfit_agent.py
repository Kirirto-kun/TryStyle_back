import json
from pydantic_ai import Agent, ModelRetry
from typing import List
from .base import get_azure_llm, Outfit, OutfitItem
from src.database import get_db_session
from src.models.clothing import ClothingItem
from src.models.product import Product as DBProduct
from src.models.store import Store as DBStore
from pydantic_ai.messages import ModelMessage


# Cache for outfit agents by user_id
_outfit_agents_cache = {}


class WardrobeManager:
    """A class to manage wardrobe-related tools, ensuring they have user context."""

    def __init__(self, user_id: int, db_session=None):
        if not isinstance(user_id, int):
            raise TypeError("user_id must be an integer.")
        self.user_id = user_id
        # Use provided session or create a new one for this manager
        self.db = db_session if db_session is not None else get_db_session()
        self._owns_session = db_session is None  # Track if we created the session

    def close_session(self):
        """Explicitly close the database session if we own it."""
        if hasattr(self, 'db') and self._owns_session:
            try:
                self.db.close()
            except Exception as e:
                print(f"Error closing database session in WardrobeManager: {e}")

    def __del__(self):
        """Cleanup session on object destruction as fallback."""
        if hasattr(self, '_owns_session') and self._owns_session:
            self.close_session()

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

    def get_catalog_items(self) -> str:
        """
        Retrieves catalog items from the store when user wardrobe is empty.
        Converts Product objects to clothing-like format with correct image URLs.
        """
        print(f"Fetching catalog items for outfit recommendations")
        try:
            # Импортируем все модели для избежания ошибок SQLAlchemy
            from src.models.review import Review
            from src.models.user import User
            from src.models.clothing import ClothingItem
            from src.models.chat import Chat, Message
            from src.models.tryon import TryOn
            from src.models.waitlist import WaitListItem
            
            # Получаем активные товары из каталога
            products = self.db.query(DBProduct).join(DBStore).filter(
                DBProduct.is_active == True,
                DBProduct.stock_quantity > 0
            ).order_by(DBProduct.name).all()

            if not products:
                return json.dumps({
                    "status": "success",
                    "catalog": [],
                    "total_items": 0,
                    "message": "No catalog items available."
                })

            # Конвертируем товары каталога в формат для образов
            catalog_items = []
            categories = {}
            
            for product in products:
                # ИСПРАВЛЕНИЕ: Правильно обрабатываем изображения из каталога
                image_url = ""
                if product.image_urls and isinstance(product.image_urls, list):
                    # Берем первое валидное изображение
                    valid_images = [img for img in product.image_urls if img and img.strip()]
                    if valid_images:
                        image_url = valid_images[0]
                
                # Мапируем категории товаров к категориям одежды
                category_mapping = {
                    "Рубашки": "Tops",
                    "Футболки": "Tops", 
                    "Джемперы": "Tops",
                    "Толстовки": "Tops",
                    "Брюки": "Bottoms",
                    "Шорты": "Bottoms",
                    "Джинсы": "Bottoms",
                    "Куртки": "Outerwear",
                    "Спорт": "Activewear",
                    "Майки": "Activewear"
                }
                outfit_category = category_mapping.get(product.category, "Tops")
                
                item_data = {
                    "name": product.name,
                    "image_url": image_url,  # ИСПРАВЛЕНИЕ: Передаем валидный URL изображения
                    "category": outfit_category,
                    "features": product.features or [],
                    "price": f"₸{product.price:,.0f}",
                    "store": f"{product.store.name}, {product.store.city}"
                }
                catalog_items.append(item_data)
                
                # Count by category for better outfit planning
                categories[outfit_category] = categories.get(outfit_category, 0) + 1

            return json.dumps({
                "status": "success",
                "catalog": catalog_items,
                "total_items": len(catalog_items),
                "categories": categories,
                "message": f"Found {len(catalog_items)} catalog items across {len(categories)} categories for outfit recommendations."
            })
            
        except Exception as e:
            print(f"An error occurred in get_catalog_items: {e}")
            return json.dumps(
                {"status": "error", "message": "An error occurred while fetching catalog items."}
            )


def create_outfit_agent(user_id: int, db_session=None) -> Agent:
    """
    Creates or returns a cached outfit recommendation agent for a specific user.
    Enhanced with strict structured output validation and conversation context awareness.
    
    Args:
        user_id: The ID of the user
        db_session: Optional database session to use (for proper session management)
        
    Returns:
        Agent: Configured outfit recommendation agent (cached per user) with context awareness
    """
    global _outfit_agents_cache
    
    # Check if we already have an agent for this user
    if user_id in _outfit_agents_cache:
        return _outfit_agents_cache[user_id]
    
    # Create new agent for this user with proper session management
    wardrobe_manager = WardrobeManager(user_id=user_id, db_session=db_session)
    
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
1. First, use get_user_wardrobe tool to check user's clothing items
2. If wardrobe is empty or insufficient, use get_catalog_items tool to access store catalog
3. Analyze conversation history for style preferences and feedback
4. Create outfits from available items (wardrobe or catalog)
5. Balance user's stated preferences with styling best practices
6. Provide clear styling rationale that references context when relevant

PREFERENCE LEARNING:
- Color preferences: Track which colors user likes/dislikes
- Style preferences: Note if user prefers casual vs formal, loose vs fitted, etc.
- Occasion feedback: Learn user's specific needs for different events
- Comfort preferences: Remember if user values comfort over style or vice versa
- Accessory preferences: Note if user likes minimal or statement accessories

UPDATED VALIDATION RULES:
- If wardrobe is empty: use catalog items to create outfit recommendations
- Prioritize user's wardrobe items when available, supplement with catalog if needed
- Ensure outfit items have valid categories: Tops, Bottoms, Outerwear, Footwear, Accessories, Dresses, Activewear
- All text fields must meet length requirements (no empty or too long content)
- Each outfit should be practical and stylistically coherent
- CRITICAL: Always include valid image_url for each OutfitItem (never use empty strings)

IMAGE URL REQUIREMENTS:
- Every OutfitItem MUST have a valid, non-empty image_url
- Use the image_url provided in wardrobe or catalog data
- If no image_url available, skip that item rather than using empty string

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
        tools=[wardrobe_manager.get_user_wardrobe, wardrobe_manager.get_catalog_items],
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
            
            # КРИТИЧЕСКАЯ ВАЛИДАЦИЯ: image_url не должен быть пустым
            if not item.image_url or not item.image_url.strip():
                print(f"⚠️  Пропускаем товар '{item.name}' - пустой image_url")
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


async def recommend_outfit(user_id: int, request: str = "What should I wear today?", message_history: List[ModelMessage] = None, db_session=None) -> Outfit:
    """
    Get outfit recommendations for a user based on their wardrobe with conversation context awareness.
    Now understands conversation history for better contextual outfit recommendations!
    
    Args:
        user_id: The ID of the user
        request: The specific outfit request (optional)
        message_history: Optional conversation history for context and preference learning
        db_session: Optional database session to use (for proper session management)
        
    Returns:
        Outfit: Strictly validated outfit recommendation with context awareness
    """
    db = None
    wardrobe_manager = None
    
    try:
        # Use provided session or create a new one
        db = db_session if db_session is not None else get_db_session()
        owns_session = db_session is None
        
        # Create agent with proper session management
        agent = create_outfit_agent(user_id, db_session=db)
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
    finally:
        # Clean up session if we created it
        if db and db_session is None:
            try:
                db.close()
            except Exception as e:
                print(f"Error closing database session in recommend_outfit: {e}") 