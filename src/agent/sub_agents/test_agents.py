"""
Простые тесты для проверки работы саб-агентов.
Запустите этот файл для проверки базовой функциональности.
"""
import asyncio
import json
from coordinator_agent import coordinate_request


async def test_search_agent():
    """Тест агента поиска товаров"""
    print("🔍 Тестируем SearchAgent...")
    try:
        response = await coordinate_request("Find me a black t-shirt", user_id=1)
        print("✅ SearchAgent работает!")
        print(f"Тип результата: {type(response.result).__name__}")
        return True
    except Exception as e:
        print(f"❌ Ошибка в SearchAgent: {e}")
        return False


async def test_outfit_agent():
    """Тест агента рекомендаций одежды"""
    print("\n👔 Тестируем OutfitAgent...")
    try:
        response = await coordinate_request("What should I wear today?", user_id=1)
        print("✅ OutfitAgent работает!")
        print(f"Тип результата: {type(response.result).__name__}")
        return True
    except Exception as e:
        print(f"❌ Ошибка в OutfitAgent: {e}")
        return False


async def test_general_agent():
    """Тест агента общих вопросов"""
    print("\n💬 Тестируем GeneralAgent...")
    try:
        response = await coordinate_request("Hello, how are you?", user_id=1)
        print("✅ GeneralAgent работает!")
        print(f"Тип результата: {type(response.result).__name__}")
        return True
    except Exception as e:
        print(f"❌ Ошибка в GeneralAgent: {e}")
        return False


async def test_request_classification():
    """Тест классификации запросов"""
    print("\n🤖 Тестируем классификацию запросов...")
    from coordinator_agent import RequestClassifier
    
    test_cases = [
        ("Find me a winter jacket", "search"),
        ("What should I wear today?", "outfit"),
        ("Hello, how are you?", "general"),
        ("I need to buy new shoes", "search"),
        ("Help me coordinate my wardrobe", "outfit"),
        ("What is the weather like?", "general"),
    ]
    
    all_correct = True
    for message, expected in test_cases:
        result = RequestClassifier.classify_request(message)
        if result == expected:
            print(f"✅ '{message}' -> {result}")
        else:
            print(f"❌ '{message}' -> {result} (ожидалось: {expected})")
            all_correct = False
    
    return all_correct


async def main():
    """Основная функция тестирования"""
    print("🚀 Запускаем тесты саб-агентов...\n")
    
    # Проверяем классификацию
    classification_ok = await test_request_classification()
    
    # Проверяем агентов (только если есть .env файл)
    try:
        search_ok = await test_search_agent()
        outfit_ok = await test_outfit_agent()
        general_ok = await test_general_agent()
        
        print(f"\n📊 Результаты тестов:")
        print(f"Классификация: {'✅' if classification_ok else '❌'}")
        print(f"SearchAgent: {'✅' if search_ok else '❌'}")
        print(f"OutfitAgent: {'✅' if outfit_ok else '❌'}")
        print(f"GeneralAgent: {'✅' if general_ok else '❌'}")
        
        if all([classification_ok, search_ok, outfit_ok, general_ok]):
            print("\n🎉 Все тесты прошли успешно!")
        else:
            print("\n⚠️ Некоторые тесты не прошли. Проверьте конфигурацию.")
            
    except Exception as e:
        print(f"\n❌ Ошибка при запуске тестов агентов: {e}")
        print("💡 Убедитесь, что у вас есть файл .env с настройками Azure OpenAI")


if __name__ == "__main__":
    asyncio.run(main()) 