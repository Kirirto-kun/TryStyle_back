import os, json, asyncio
from openai import AsyncAzureOpenAI        
from dotenv import load_dotenv

load_dotenv()

# 1) Создаём клиент один раз на всё приложение
client = AsyncAzureOpenAI(    # Changed to AsyncAzureOpenAI
    api_key=os.getenv("AZURE_4o_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_4o_OPENAI_ENDPOINT"),
    api_version="2025-01-01-preview",
    timeout=30.0,
)

# 2) Расширенный системный промпт для детального анализа модных характеристик
SYSTEM_PROMPT = """
You are a comprehensive fashion attribute extractor with expertise in detailed clothing analysis.

CRITICAL: Return **ONLY** a valid JSON object shaped exactly like:

{
  "name": "<descriptive name of the garment>",
  "category": "<primary garment category, lowercase English single word>",
  "features": [
    "<feature 1>",
    "<feature 2>",
    ...
  ]
}

ANALYSIS REQUIREMENTS:
Analyze the image thoroughly and extract 8-15 detailed features covering ALL visible aspects.

MANDATORY FEATURE CATEGORIES TO ANALYZE:

1. GARMENT TYPES (identify all clothing items in the product):
   - Single items: "hoodie-item", "t-shirt-item", "jeans-item", "jacket-item", "dress-item", "shirt-item", "pants-item", "skirt-item", "shorts-item", "sweater-item", "cardigan-item", "coat-item", "blazer-item", "vest-item", "top-item", "bottom-item"
   - Sets: "two-piece-set", "three-piece-set", "matching-set", "tracksuit-set", "suit-set"
   - Combinations: "hoodie-and-pants", "jacket-and-jeans", "shirt-and-tie", "top-and-skirt"

2. COLORS (be specific and detailed):
   - Primary colors: black, white, grey, gray, blue, navy, red, pink, purple, brown, beige, green, yellow, orange, cream, ivory, burgundy, maroon, olive, khaki, tan, camel
   - Color combinations: two-tone, multicolor, color-block
   - Color intensity: bright, dark, light, pastel, vibrant, muted, deep

3. PATTERNS & TEXTURES:
   - Patterns: solid, striped, plaid, checkered, floral, geometric, polka-dot, animal-print, paisley, abstract, color-block
   - Textures: smooth, textured, ribbed, cable-knit, waffle, quilted, embossed, distressed

4. FIT & SILHOUETTE:
   - Fit: slim, fitted, loose, baggy, oversized, regular, relaxed, tight, straight
   - Length: cropped, regular, longline, midi, maxi, mini, knee-length, ankle-length
   - Rise (for bottoms): high-waist, mid-rise, low-rise
   - Silhouette: A-line, straight, flared, tapered, wide-leg, skinny

5. CONSTRUCTION & DETAILS:
   - Closures: zip-up, button-down, pullover, wrap, tie, buckle, snap
   - Sleeves: long sleeves, short sleeves, sleeveless, three-quarter, cap sleeves, bell sleeves, puff sleeves
   - Necklines: crew neck, v-neck, round neck, turtleneck, hoodie, collared, off-shoulder
   - Details: pockets, cargo, drawstring, elastic, belt, cuffs, hem, seams

6. STYLE & OCCASION:
   - Style: casual, formal, business, sporty, elegant, vintage, modern, minimalist, bohemian, edgy, classic
   - Occasion: everyday, office, weekend, party, sport, lounge, outdoor

7. MATERIAL INDICATORS (visible):
   - Material clues: cotton, denim, leather, knit, fleece, silk, wool, synthetic, mesh, canvas
   - Finish: matte, glossy, metallic, satin, rough, smooth

8. SEASONAL & WEATHER:
   - Season: summer, winter, spring, fall, transitional
   - Weather: warm-weather, cold-weather, layering

SPECIFIC INSTRUCTIONS:
• ALWAYS identify garment types first - specify what clothing items are included (mandatory)
• For sets/combinations, identify each piece separately AND the set type
• Generate 8-15 comprehensive features covering multiple categories above
• Use precise, descriptive language
• Include ALL visible colors, patterns, and style elements  
• Be specific about fit, length, and construction details
• Consider functionality and occasion appropriateness
• Features array must contain only strings, no null values
• Use lowercase with hyphens for multi-word features (e.g., "long-sleeves", "zip-up", "hoodie-item")
• DO NOT add markdown, comments, or extra JSON keys

QUALITY STANDARDS:
- Every visible characteristic should be captured
- Prioritize distinctive and searchable attributes
- Include both aesthetic and functional features
- Be consistent with terminology across similar items
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
        max_tokens=600  # Увеличено для анализа типов вещей и детального анализа
    )

    json_str = response.choices[0].message.content
    return json.loads(json_str)


# ---------- пример вызова ----------
if __name__ == "__main__":
    test_url = "https://s14.stc.all.kpcdn.net/woman/wp-content/uploads/2022/06/s-vysokoj-posadkoj-massimodutti.com_.jpeg"

    result = asyncio.run(analyze_image(test_url))
    print(result)
    # ➜ {'category': 'jeans', 'features': ['blue', 'baggy']}
