import os, json, asyncio
from openai import AsyncAzureOpenAI        
from dotenv import load_dotenv

load_dotenv()

# 1) Создаём клиент один раз на всё приложение
client = AsyncAzureOpenAI(    # Changed to AsyncAzureOpenAI
    api_key=os.getenv("AZURE_4o_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_4o_OPENAI_ENDPOINT"),
    api_version="2025-01-01-preview" 
)

# 2) Системный prompt — жёстко фиксирует формат, чтобы пришёл чистый JSON
SYSTEM_PROMPT = """
You are a fashion attribute extractor.

Return **ONLY** a valid JSON object shaped exactly like:

{
  "name": "<name of the garment>",
  "category": "<primary garment category, lowercase English single word>",
  "features": [
    "<salient attribute 1>",
    "<salient attribute 2>",
    ...
  ]
}

• Allowed colour words: black, white, grey, blue, navy, red, pink, purple,
  brown, beige, green, yellow, orange.
• Typical features: fit (slim, loose, baggy), silhouette (straight, flared),
  length (cropped, longline), pattern (solid, striped, plaid, floral),
  distressing (ripped, distressed), rise (high-waist, mid-rise, low-rise), etc.
• Use null for unknown values.
• Do NOT add markdown, comments or extra keys.
"""

async def analyze_image(
    image_url: str,
    deployment: str = "gpt-4o"     # имя вашей Azure-деплойки
) -> dict:
    """
    Возвращает dict c ключами `category` и `features`.
    В случае ошибки бросает исключение.
    """
    response = await client.chat.completions.create(
        model=deployment,           # Azure OpenAI uses deployment name as model name
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
        response_format={"type": "json_object"},   # гарантирует JSON
        max_tokens=200
    )

    json_str = response.choices[0].message.content
    return json.loads(json_str)


# ---------- пример вызова ----------
if __name__ == "__main__":
    test_url = "https://s14.stc.all.kpcdn.net/woman/wp-content/uploads/2022/06/s-vysokoj-posadkoj-massimodutti.com_.jpeg"

    result = asyncio.run(analyze_image(test_url))
    print(result)
    # ➜ {'category': 'jeans', 'features': ['blue', 'baggy']}
