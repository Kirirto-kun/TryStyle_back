import http.client
import json
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

headers = {
  'X-API-KEY': os.getenv('GOOGLE_SERPER_API_KEY'),
  'Content-Type': 'application/json'
}
conn = http.client.HTTPSConnection("google.serper.dev")
async def google_lens_search(image_url: str, location: str = "Almaty, Almaty Province, Kazakhstan", gl: str = "kz", hl: str = "ru"):
    global conn, headers
    payload = json.dumps({
        "url": image_url,
        "location": location,
        "gl": gl,
        "hl": hl
    })

    conn.request("POST", "/lens", payload, headers)
    res = conn.getresponse()
    data = res.read()
    return data.decode("utf-8")

async def google_search(query: str, location: str = "Almaty, Kazakhstan", gl: str = "kz", hl: str = "ru"):
    global conn, headers
    payload = json.dumps({
        "q": query,
        "location": location,
        "gl": gl,
        "hl": hl
    })

    conn.request("POST", "/search", payload, headers)
    res = conn.getresponse()
    data = res.read()
    return data.decode("utf-8")

if __name__ == "__main__":
    # print(google_search("What is the capital of Kazakhstan?"))
    ans = asyncio.run(google_lens_search("https://resources.cdn-kaspi.kz/img/m/p/he2/had/86604463964190.jpg", " Almaty, Kazakhstan", "kz", "ru"))
    print(ans)
    # Сохраняем результат в файл
    with open("result.json", "w", encoding="utf-8") as f:
        f.write(ans)