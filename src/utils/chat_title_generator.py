from openai import AsyncAzureOpenAI
import os
import re


async def generate_chat_title(first_message: str) -> str:
    """Generate a short, descriptive chat title based on the first user message.

    The function leverages Azure OpenAI to create a concise title in **Russian**
    (to match the project language) containing 3-6 words that best describe the
    essence of *first_message*.

    If Azure OpenAI is not available or fails for any reason, the function
    falls back to a simple heuristic that takes the first 5-6 words of the
    message and capitalises them.
    """

    # Heuristic fallback defined inside so we can use it whenever model call fails
    def _fallback_title(msg: str) -> str:
        words = re.findall(r"\w+", msg)[:6]
        return " ".join(words).capitalize() or "Новый чат"

    # Read Azure credentials from env; if any missing – immediately fallback
    azure_api_key = os.getenv("AZURE_API_KEY")
    azure_endpoint = os.getenv("AZURE_API_BASE")
    azure_api_version = os.getenv("AZURE_API_VERSION")
    deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME")

    if not all([azure_api_key, azure_endpoint, azure_api_version, deployment_name]):
        # Required env vars are missing, skip remote call
        return _fallback_title(first_message)

    try:
        client = AsyncAzureOpenAI(
            api_key=azure_api_key,
            azure_endpoint=azure_endpoint,
            api_version=azure_api_version,
        )

        prompt_system = (
            "Ты придумываешь максимально короткие и понятные названия чатов (1–3 слова, без кавычек). "
            "Выбери только самые важные слова из запроса."
        )
        prompt_user = (
            f"Создай название на основе следующего сообщения пользователя: \n\n{first_message}"
        )

        response = await client.chat.completions.create(
            model=deployment_name,  # В Azure используется имя deployment
            messages=[
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": prompt_user},
            ],
            max_tokens=10,
            temperature=0.7,
        )

        title = response.choices[0].message.content.strip()
        # Удаляем лишние кавычки, если они вдруг появились
        title = title.strip('"').strip("'")
        # Ограничиваем длину в 100 символов
        return title[:100] if title else _fallback_title(first_message)

    except Exception:
        # На случай любых ошибок (сетевых, квот и т.д.)
        return _fallback_title(first_message) 