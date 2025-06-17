import os
from typing import Union
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider

# Load environment variables
load_dotenv()


# Shared Pydantic Models
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
    products: list[Product] = Field(..., description="A list of products found.")


class Outfit(BaseModel):
    outfit_description: str = Field(
        ..., description="A friendly description of the outfit."
    )
    items: list[dict] = Field(
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


# Combined Output Model for the main coordinator
class AgentResponse(BaseModel):
    """The final response object to the user."""
    result: Union[ProductList, Outfit, GeneralResponse] = Field(
        ..., description="The result of the agent's work, can be a list of products, an outfit, or a general response."
    )


def get_azure_llm() -> OpenAIModel:
    """
    Creates and returns a configured Azure OpenAI model instance.
    
    Returns:
        OpenAIModel: Configured Azure OpenAI model
    """
    return OpenAIModel(
        model_name=os.environ["AZURE_DEPLOYMENT_NAME"],
        provider=AzureProvider(
            azure_endpoint=os.environ["AZURE_API_BASE"],
            api_version=os.environ["AZURE_API_VERSION"],  
            api_key=os.environ["AZURE_API_KEY"],
        ),
    ) 