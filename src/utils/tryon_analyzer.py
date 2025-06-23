import os
import asyncio
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# Reuse the client configuration
client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_4o_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_4o_OPENAI_ENDPOINT"),
    api_version="2025-01-01-preview"
)

# New system prompt specifically for try-on description
SYSTEM_PROMPT = """
You are a fashion expert providing a detailed description of a garment from an image.
This description will be used as a prompt for a virtual try-on service, so it must be concise yet comprehensive, capturing all key visual attributes.
Describe the clothing's category, style, color, material, and any notable patterns or features.
Provide only the description as a single, clean string. Do not add any extra text or labels.

Example: "A white short-sleeve cotton t-shirt with a small graphic print on the chest."
Example: "Blue denim high-waisted skinny jeans with ripped details on the knees."
Example: "A black and red plaid flannel long-sleeve button-up shirt."
"""

async def analyze_image_for_tryon(
    image_url: str,
    deployment: str = "gpt-4o"
) -> str:
    """
    Analyzes a clothing image and returns a concise textual description for a try-on service.
    Returns a string description.
    """
    response = await client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    }
                ]
            }
        ],
        max_tokens=100
    )

    description = response.choices[0].message.content.strip()
    return description 