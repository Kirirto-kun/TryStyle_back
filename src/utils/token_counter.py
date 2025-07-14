import os
import tiktoken
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_tiktoken_model_name(azure_deployment_name: Optional[str] = None) -> str:
    """
    Определяет имя модели для tiktoken на основе Azure deployment name.
    
    Args:
        azure_deployment_name: Имя deployment в Azure OpenAI
        
    Returns:
        str: Имя модели для tiktoken (gpt-4, gpt-3.5-turbo, etc.)
    """
    if not azure_deployment_name:
        azure_deployment_name = os.environ.get("AZURE_DEPLOYMENT_NAME", "")
    
    # Приводим к нижнему регистру для проверки
    deployment_lower = azure_deployment_name.lower()
    
    # Маппинг Azure deployment names к tiktoken model names
    if "gpt-4o" in deployment_lower:
        return "gpt-4o"
    elif "gpt-4" in deployment_lower:
        return "gpt-4"
    elif "gpt-35-turbo" in deployment_lower or "gpt-3.5-turbo" in deployment_lower:
        return "gpt-3.5-turbo"
    else:
        # Fallback на gpt-4 для неизвестных моделей
        return "gpt-4"


def count_tokens(text: str, model: Optional[str] = None) -> int:
    """
    Подсчитывает количество токенов в тексте.
    
    Args:
        text: Текст для подсчета токенов
        model: Имя модели для tiktoken (если не указано, определяется автоматически)
        
    Returns:
        int: Количество токенов в тексте
    """
    if not text or not isinstance(text, str):
        return 0
    
    try:
        if not model:
            model = get_tiktoken_model_name()
        
        # Получаем encoder для модели
        encoding = tiktoken.encoding_for_model(model)
        
        # Подсчитываем токены
        tokens = encoding.encode(text)
        return len(tokens)
        
    except Exception as e:
        print(f"Error counting tokens: {e}")
        # Fallback: приблизительная оценка (4 символа ≈ 1 токен)
        return len(text) // 4


def count_message_tokens(message: str, response: str = "", model: Optional[str] = None) -> Dict[str, int]:
    """
    Подсчитывает токены для входящего сообщения и ответа.
    
    Args:
        message: Входящее сообщение пользователя
        response: Ответ агента (опционально)
        model: Имя модели для tiktoken
        
    Returns:
        dict: Словарь с количеством токенов {input_tokens, output_tokens, total_tokens}
    """
    if not model:
        model = get_tiktoken_model_name()
    
    input_tokens = count_tokens(message, model)
    output_tokens = count_tokens(response, model) if response else 0
    total_tokens = input_tokens + output_tokens
    
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "model_used": model
    }


def estimate_cost(input_tokens: int, output_tokens: int, model: str = "gpt-4") -> Dict[str, float]:
    """
    Оценивает примерную стоимость использования токенов.
    
    Args:
        input_tokens: Количество входных токенов
        output_tokens: Количество выходных токенов  
        model: Модель для расчета стоимости
        
    Returns:
        dict: Стоимость в USD {input_cost, output_cost, total_cost}
    """
    # Примерные цены за 1K токенов (может отличаться в зависимости от региона Azure)
    pricing = {
        "gpt-4o": {"input": 0.005, "output": 0.015},  # $5/$15 per 1M tokens
        "gpt-4": {"input": 0.03, "output": 0.06},      # $30/$60 per 1M tokens  
        "gpt-3.5-turbo": {"input": 0.001, "output": 0.002}  # $1/$2 per 1M tokens
    }
    
    # Получаем цены для модели (fallback на gpt-4)
    model_pricing = pricing.get(model, pricing["gpt-4"])
    
    input_cost = (input_tokens / 1000) * model_pricing["input"]
    output_cost = (output_tokens / 1000) * model_pricing["output"] 
    total_cost = input_cost + output_cost
    
    return {
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "total_cost_usd": round(total_cost, 6),
        "model": model
    }


def get_token_usage_summary(message: str, response: str = "", include_cost: bool = False) -> Dict[str, Any]:
    """
    Получает полную сводку по использованию токенов.
    
    Args:
        message: Входящее сообщение
        response: Ответ агента
        include_cost: Включать ли оценку стоимости
        
    Returns:
        dict: Полная сводка использования токенов
    """
    model = get_tiktoken_model_name()
    token_counts = count_message_tokens(message, response, model)
    
    summary = {
        "tokens": token_counts,
        "message_length": len(message),
        "response_length": len(response) if response else 0
    }
    
    if include_cost:
        cost_info = estimate_cost(
            token_counts["input_tokens"],
            token_counts["output_tokens"], 
            model
        )
        summary["cost_estimate"] = cost_info
    
    return summary 