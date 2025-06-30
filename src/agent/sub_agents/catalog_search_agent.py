import asyncio
from typing import List, Optional
from pydantic_ai import Agent, ModelRetry, RunContext
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, and_, or_
from dataclasses import dataclass

from .base import get_azure_llm, ProductList, Product, MessageHistory
from src.models.product import Product as DBProduct
from src.models.store import Store as DBStore
from pydantic_ai.messages import ModelMessage


@dataclass
class CatalogSearchDependencies:
    """Dependencies for the catalog search agent."""
    user_id: int
    db: Session
    chat_id: int


# Cached catalog search agent instance
_catalog_search_agent_instance = None

def get_catalog_search_agent() -> Agent:
    """
    Returns a catalog search agent that searches products in the local database.
    This agent specializes in finding products from the internal H&M catalog.
    """
    global _catalog_search_agent_instance
    
    if _catalog_search_agent_instance is None:
        _catalog_search_agent_instance = Agent(
            get_azure_llm(),
            deps_type=CatalogSearchDependencies,
            output_type=ProductList,
            tools=[search_internal_catalog, recommend_styling_items],
            system_prompt="""You are a specialized catalog search agent for H&M fashion store in Kazakhstan.

Your job is to help users find clothing items from the local H&M catalog in Almaty and Aktobe.

CATALOG INFORMATION:
- You have access to H&M products in Kazakhstan
- All prices are in Kazakhstani Tenge (₸)
- Stores located in Almaty and Aktobe
- Product categories: Shirts, Shorts, Pants, Jackets, T-shirts, Sportswear, Sweaters, etc.
- Brands: Primarily H&M products
- Real product images and detailed descriptions available

REQUEST TYPES TO HANDLE:

1. DIRECT PRODUCT SEARCH:
   - "I want business pants" → search for formal/business pants
   - "Looking for a warm jacket" → search for jackets with warm descriptions
   - "Need a black t-shirt" → search by color and category
   - Use search_internal_catalog tool

2. STYLING RECOMMENDATIONS:
   - "What goes well with a black t-shirt?" → find complementary items
   - "What can I style with this item?" → suggest matching pieces
   - "Complete this outfit" → find missing pieces
   - Use recommend_styling_items tool

SEARCH STRATEGY:
- Analyze user's request to understand: item type, color, style, occasion
- Search by: name, description, category, brand, colors
- Consider: price range, sizes available, stock status
- Prioritize items that best match the user's needs
- Return maximum 10 most relevant items

RESPONSE FORMAT:
- Always return ProductList with relevant items from local catalog
- Include product names, prices in Tenge, descriptions, and image URLs
- Explain why each item matches the user's request
- Mention store availability (Almaty/Aktobe)

Remember: Only search in the local H&M catalog, never external sources.""",
            retries=3
        )
        
        # Add output validator
        @_catalog_search_agent_instance.output_validator
        async def validate_catalog_output(output: ProductList) -> ProductList:
            """Validate catalog search output."""
            if not isinstance(output, ProductList):
                raise ModelRetry("Output must be a valid ProductList object")
            
            # Ensure reasonable number of products
            if len(output.products) > 10:
                output.products = output.products[:10]
            
            # Validate search query exists
            if not output.search_query or len(output.search_query.strip()) < 2:
                raise ModelRetry("Search query must be provided and meaningful")
            
            # Ensure total_found is valid
            if output.total_found < 0:
                output.total_found = len(output.products)
            
            return output
    
    return _catalog_search_agent_instance


async def search_internal_catalog(
    ctx: RunContext[CatalogSearchDependencies], 
    search_query: str,
    category: Optional[str] = None,
    color: Optional[str] = None,
    price_max: Optional[float] = None,
    occasion: Optional[str] = None
) -> ProductList:
    """
    Search for products in the internal H&M catalog database.
    
    Args:
        search_query: User's search query
        category: Optional category filter (e.g., "Shirts", "Pants")
        color: Optional color filter (e.g., "Black", "Blue") 
        price_max: Optional maximum price filter
        occasion: Optional occasion filter (e.g., "business", "casual")
        
    Returns:
        ProductList: List of matching products from local catalog
    """
    try:
        db = ctx.deps.db
        print(f"🔍 Searching internal catalog for: {search_query}")
        
        # Build base query with active products and store info
        query_obj = db.query(DBProduct).join(DBStore).filter(
            DBProduct.is_active == True,
            DBProduct.stock_quantity > 0  # Only in-stock items
        )
        
        # Text search across multiple fields
        if search_query:
            search_terms = search_query.lower().strip()
            search_filter = or_(
                DBProduct.name.ilike(f"%{search_terms}%"),
                DBProduct.description.ilike(f"%{search_terms}%"),
                DBProduct.category.ilike(f"%{search_terms}%"),
                DBProduct.brand.ilike(f"%{search_terms}%")
            )
            query_obj = query_obj.filter(search_filter)
        
        # Apply filters
        if category:
            query_obj = query_obj.filter(DBProduct.category.ilike(f"%{category}%"))
            
        if color:
            # Search in colors JSON array
            query_obj = query_obj.filter(
                func.lower(func.cast(DBProduct.colors, db.Text)).like(f"%{color.lower()}%")
            )
            
        if price_max:
            query_obj = query_obj.filter(DBProduct.price <= price_max)
        
        # Sort by relevance (rating desc, then by price asc)
        query_obj = query_obj.order_by(desc(DBProduct.rating), asc(DBProduct.price))
        
        # Limit results
        db_products = query_obj.limit(10).all()
        
        print(f"   Found {len(db_products)} matching products")
        
                 # Convert to Product schema format with full information
        products = []
        for db_product in db_products:
            # Format prices in Tenge
            price_str = f"₸{db_product.price:,.0f}"
            original_price_str = None
            if db_product.original_price and db_product.original_price > db_product.price:
                original_price_str = f"₸{db_product.original_price:,.0f}"
            
            # Create product object with full catalog information
            product = Product(
                name=db_product.name,
                price=price_str,
                description=db_product.description or "Стильная вещь от H&M",
                link=f"/products/{db_product.id}",  # Internal link
                image_urls=db_product.image_urls or [],  # Product images for frontend
                original_price=original_price_str,
                store_name=db_product.store.name,
                store_city=db_product.store.city,
                sizes=db_product.sizes or [],
                colors=db_product.colors or [],
                in_stock=db_product.stock_quantity > 0
            )
            products.append(product)
        
        return ProductList(
            products=products,
            search_query=search_query,
            total_found=len(db_products)
        )
        
    except Exception as e:
        print(f"❌ Error searching internal catalog: {e}")
        return ProductList(
            products=[],
            search_query=search_query,
            total_found=0
        )


async def recommend_styling_items(
    ctx: RunContext[CatalogSearchDependencies],
    base_item: str,
    style_type: str = "casual"
) -> ProductList:
    """
    Recommend items from catalog that would style well with a given base item.
    
    Args:
        base_item: The item to create styling recommendations for
        style_type: Style preference (casual, business, evening, etc.)
        
    Returns:
        ProductList: Recommended styling items from catalog
    """
    try:
        db = ctx.deps.db
        print(f"🎨 Finding styling recommendations for: {base_item}")
        
        # Analyze base item to determine what complements it
        base_lower = base_item.lower()
        
        # Define styling rules
        styling_suggestions = []
        
        if any(word in base_lower for word in ["футболка", "t-shirt", "майка"]):
            # For t-shirts, suggest: jackets, pants, shorts
            styling_suggestions = ["куртка", "джинсы", "брюки", "шорты", "пиджак"]
        elif any(word in base_lower for word in ["рубашка", "shirt"]):
            # For shirts, suggest: pants, jackets, sweaters
            styling_suggestions = ["брюки", "джинсы", "куртка", "джемпер"]
        elif any(word in base_lower for word in ["брюки", "pants", "джинсы"]):
            # For pants, suggest: shirts, t-shirts, jackets
            styling_suggestions = ["рубашка", "футболка", "куртка", "джемпер"]
        elif any(word in base_lower for word in ["куртка", "jacket"]):
            # For jackets, suggest: shirts, pants, t-shirts
            styling_suggestions = ["рубашка", "футболка", "брюки", "джинсы"]
        else:
            # Default suggestions
            styling_suggestions = ["рубашка", "брюки", "куртка", "футболка"]
        
        # Search for complementary items
        all_products = []
        
        for suggestion in styling_suggestions[:3]:  # Top 3 categories
            query_obj = db.query(DBProduct).join(DBStore).filter(
                DBProduct.is_active == True,
                DBProduct.stock_quantity > 0,
                or_(
                    DBProduct.name.ilike(f"%{suggestion}%"),
                    DBProduct.category.ilike(f"%{suggestion}%"),
                    DBProduct.description.ilike(f"%{suggestion}%")
                )
            ).order_by(desc(DBProduct.rating)).limit(3)
            
            products = query_obj.all()
            all_products.extend(products)
        
        # Remove duplicates and limit
        seen_ids = set()
        unique_products = []
        for product in all_products:
            if product.id not in seen_ids:
                unique_products.append(product)
                seen_ids.add(product.id)
        
        unique_products = unique_products[:8]  # Max 8 recommendations
        
        print(f"   Found {len(unique_products)} styling recommendations")
        
                 # Convert to Product schema format with full styling information
        recommendations = []
        for db_product in unique_products:
            # Format prices
            price_str = f"₸{db_product.price:,.0f}"
            original_price_str = None
            if db_product.original_price and db_product.original_price > db_product.price:
                original_price_str = f"₸{db_product.original_price:,.0f}"
            
            # Add styling context to description
            style_desc = f"Отлично сочетается с {base_item}. {db_product.description or 'Стильная вещь от H&M'}"
            
            product = Product(
                name=db_product.name,
                price=price_str,
                description=style_desc,
                link=f"/products/{db_product.id}",
                image_urls=db_product.image_urls or [],
                original_price=original_price_str,
                store_name=db_product.store.name,
                store_city=db_product.store.city,
                sizes=db_product.sizes or [],
                colors=db_product.colors or [],
                in_stock=db_product.stock_quantity > 0
            )
            recommendations.append(product)
        
        return ProductList(
            products=recommendations,
            search_query=f"Стилизация для: {base_item}",
            total_found=len(recommendations)
        )
        
    except Exception as e:
        print(f"❌ Error getting styling recommendations: {e}")
        return ProductList(
            products=[],
            search_query=f"Стилизация для: {base_item}",
            total_found=0
        )


async def search_catalog_products(
    message: str, 
    user_id: int, 
    db: Session, 
    chat_id: int, 
    message_history: List[ModelMessage] = None
) -> ProductList:
    """
    Main entry point for catalog search with conversation context.
    
    Args:
        message: User's search message
        user_id: User ID
        db: Database session
        chat_id: Chat ID
        message_history: Previous conversation for context
        
    Returns:
        ProductList: Search results from internal catalog
    """
    try:
        # Create dependencies
        deps = CatalogSearchDependencies(
            user_id=user_id,
            db=db,
            chat_id=chat_id
        )
        
        # Get catalog search agent
        catalog_agent = get_catalog_search_agent()
        
        # Run the agent with conversation context
        result = await catalog_agent.run(
            message,
            deps=deps,
            message_history=message_history or []
        )
        
        return result.data
        
    except Exception as e:
        print(f"❌ Error in search_catalog_products: {e}")
        return ProductList(
            products=[],
            search_query=message,
            total_found=0
        ) 