import os
from typing import Union, List, Literal, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator, field_validator
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

# Global cached instances for performance optimization
_azure_llm_instance = None
_azure_openai_client = None

# Message History Model
class MessageHistory(BaseModel):
    """Model for chat message history."""
    messages: List[dict] = Field(
        default_factory=list,
        description="List of previous messages in the conversation"
    )

    def to_pydantic_ai_messages(self) -> List[ModelMessage]:
        """Convert database messages to PydanticAI message format."""
        pydantic_messages = []
        for msg in self.messages:
            if msg["role"] == "user":
                pydantic_messages.append(
                    ModelRequest(
                        parts=[
                            UserPromptPart(content=msg["content"])
                        ]
                    )
                )
            else:  # assistant
                pydantic_messages.append(
                    ModelResponse(
                        parts=[
                            TextPart(content=msg["content"])
                        ]
                    )
                )
        return pydantic_messages


# Enhanced Structured Output Models
class Product(BaseModel):
    """Structured model for product information with strict validation."""
    name: str = Field(
        ..., 
        min_length=1,
        max_length=200,
        description="Product/service name - must be descriptive and accurate"
    )
    price: str = Field(
        ...,
        description='Price with currency symbol (e.g. "$29.99", "€15.00", "₸16,500") or exactly "Price not found" if not available'
    )
    description: str = Field(
        ..., 
        min_length=10,
        max_length=500,
        description="Concise, informative description highlighting key features (10-500 chars)"
    )
    link: str = Field(
        ..., 
        description="URL to the product page (can be relative /products/1 or absolute https://...)"
    )
    # NEW FIELDS FOR CATALOG PRODUCTS:
    image_urls: List[str] = Field(
        default_factory=list,
        description="List of product image URLs for display on frontend"
    )
    original_price: Optional[str] = Field(
        default=None,
        description="Original price before discount (if applicable)"
    )
    store_name: Optional[str] = Field(
        default=None,
        description="Name of the store selling this product"
    )
    store_city: Optional[str] = Field(
        default=None,
        description="City where the store is located"
    )
    sizes: List[str] = Field(
        default_factory=list,
        description="Available sizes for this product"
    )
    colors: List[str] = Field(
        default_factory=list,
        description="Available colors for this product"
    )
    in_stock: bool = Field(
        default=True,
        description="Whether the product is currently in stock"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or v.isspace():
            raise ValueError('Product name cannot be empty or whitespace')
        return v.strip()

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        if not v or v.isspace():
            raise ValueError('Description cannot be empty or whitespace')
        return v.strip()


class ProductList(BaseModel):
    """Structured list of products with validation."""
    products: List[Product] = Field(
        ..., 
        min_items=0,
        max_items=10,
        description="List of found products (0-10 items max for performance)"
    )
    search_query: str = Field(
        default="",
        description="Original search query that was processed"
    )
    total_found: int = Field(
        default=0,
        ge=0,
        description="Total number of products found"
    )

    @field_validator('products')
    @classmethod
    def validate_products(cls, v: List[Product]) -> List[Product]:
        # Remove duplicates based on name + link combination
        seen = set()
        unique_products = []
        for product in v:
            key = (product.name.lower().strip(), product.link)
            if key not in seen:
                seen.add(key)
                unique_products.append(product)
        return unique_products


class OutfitItem(BaseModel):
    """Structured model for outfit item with strict validation."""
    name: str = Field(
        ..., 
        min_length=1,
        max_length=100,
        description="Name of the clothing item"
    )
    category: Literal["Tops", "Bottoms", "Outerwear", "Footwear", "Accessories", "Dresses", "Activewear"] = Field(
        ...,
        description="Category of the clothing item - must be one of the specified categories"
    )
    image_url: str = Field(
        ..., 
        description="URL to the image of the clothing item"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or v.isspace():
            raise ValueError('Item name cannot be empty')
        return v.strip()


class Outfit(BaseModel):
    """Structured model for outfit recommendation with enhanced validation."""
    outfit_description: str = Field(
        ..., 
        min_length=20,
        max_length=300,
        description="Friendly, detailed description of the outfit and its style (20-300 chars)"
    )
    items: List[OutfitItem] = Field(
        ...,
        min_items=0,
        max_items=8,
        description="List of clothing items in the outfit (max 8 items for practicality)"
    )
    reasoning: str = Field(
        ..., 
        min_length=15,
        max_length=200,
        description="Brief explanation of why these items work together and the styling logic (15-200 chars)"
    )
    occasion: Literal["casual", "formal", "business", "evening", "sport", "weekend", "date", "work"] = Field(
        default="casual",
        description="Occasion/style type for this outfit"
    )

    @field_validator('outfit_description', 'reasoning')
    @classmethod
    def validate_text_fields(cls, v: str) -> str:
        if not v or v.isspace():
            raise ValueError('Text field cannot be empty')
        return v.strip()


class GeneralResponse(BaseModel):
    """Structured model for general responses with validation."""
    response: str = Field(
        ..., 
        min_length=5,
        max_length=1000,
        description="Helpful, informative, and friendly response to the user's query (5-1000 chars)"
    )
    response_type: Literal["answer", "clarification", "suggestion", "greeting", "error"] = Field(
        default="answer",
        description="Type of response being provided"
    )
    confidence: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Confidence level in the response (0.0 to 1.0)"
    )

    @field_validator('response')
    @classmethod
    def validate_response(cls, v: str) -> str:
        if not v or v.isspace():
            raise ValueError('Response cannot be empty')
        return v.strip()


# Combined Output Model for the main coordinator
class AgentResponse(BaseModel):
    """The final structured response object to the user with strict typing."""
    result: Union[ProductList, Outfit, GeneralResponse] = Field(
        ..., 
        description="The validated result from the appropriate specialized agent"
    )
    agent_type: Literal["search", "outfit", "general"] = Field(
        ...,
        description="Which agent type processed this request"
    )
    processing_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Time taken to process the request in milliseconds"
    )
    input_tokens: int = Field(
        default=0,
        ge=0,
        description="Number of tokens in the input message"
    )
    output_tokens: int = Field(
        default=0,
        ge=0,
        description="Number of tokens in the output response"
    )
    total_tokens: int = Field(
        default=0,
        ge=0,
        description="Total number of tokens used (input + output)"
    )


def get_azure_llm() -> OpenAIModel:
    """
    Creates and returns a cached Azure OpenAI model instance for better performance.
    Uses singleton pattern to avoid creating new clients on every call.
    
    Returns:
        OpenAIModel: Cached Azure OpenAI model
    """
    global _azure_llm_instance
    
    if _azure_llm_instance is None:
        _azure_llm_instance = OpenAIModel(
            model_name=os.environ["AZURE_DEPLOYMENT_NAME"],
            provider=AzureProvider(
                azure_endpoint=os.environ["AZURE_API_BASE"],
                api_version=os.environ["AZURE_API_VERSION"],  
                api_key=os.environ["AZURE_API_KEY"],
            ),
        )
    
    return _azure_llm_instance


def get_azure_openai_client() -> AzureOpenAI:
    """
    Creates and returns a cached Azure OpenAI client for direct API calls.
    Uses singleton pattern to avoid creating new clients on every call.
    
    Returns:
        AzureOpenAI: Cached Azure OpenAI client for structured outputs
    """
    global _azure_openai_client
    
    if _azure_openai_client is None:
        _azure_openai_client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_API_BASE"],
            api_key=os.environ["AZURE_API_KEY"],
            api_version=os.environ["AZURE_API_VERSION"]  # Version that supports structured outputs
        )
    
    return _azure_openai_client 