import os
import asyncio
import json
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# Reuse the client configuration
client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_4o_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_4o_OPENAI_ENDPOINT"),
    api_version="2025-01-01-preview",
    timeout=30.0,
)

# New system prompt specifically for try-on description
SYSTEM_PROMPT = """
You are a fashion expert providing a detailed description and category of a garment from an image.
This information will be used for a virtual try-on service.

Return **ONLY** a valid JSON object shaped exactly like:

{
  "garment_des": "<concise yet comprehensive description of the garment>",
  "category": "<'upper_body' or 'lower_body' or 'dresses'>"
}

- The `garment_des` should capture all key visual attributes like style, color, material, and any notable patterns or features.
- The `category` must be one of "upper_body", "lower_body", or "dresses".
- Do NOT add markdown, comments or extra keys.

Example for a T-shirt:
{
  "garment_des": "A white short-sleeve cotton t-shirt with a small graphic print on the chest.",
  "category": "upper_body"
}

Example for jeans:
{
  "garment_des": "Blue denim high-waisted skinny jeans with ripped details on the knees.",
  "category": "lower_body"
}
"""

async def analyze_image_for_tryon(
    image_url: str,
    deployment: str = "gpt-4o"
) -> dict:
    """
    Analyzes a clothing image and returns a dictionary with description and category.
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
        response_format={"type": "json_object"},
        max_tokens=200
    )

    json_str = response.choices[0].message.content
    return json.loads(json_str) 