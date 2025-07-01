"""
Простые тесты для проверки работы саб-агентов.
Запустите этот файл для проверки базовой функциональности.
"""
import asyncio
import json
from coordinator_agent import coordinate_request


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


async def main():
    """Основная функция тестирования"""
    print("🚀 Запускаем тесты саб-агентов...\n")
    
    # Проверяем агентов (только если есть .env файл)
    try:
        outfit_ok = await test_outfit_agent()
        general_ok = await test_general_agent()
        
        print(f"\n📊 Результаты тестов:")
        print(f"OutfitAgent: {'✅' if outfit_ok else '❌'}")
        print(f"GeneralAgent: {'✅' if general_ok else '❌'}")
        
        if all([outfit_ok, general_ok]):
            print("\n🎉 Все тесты прошли успешно!")
        else:
            print("\n⚠️ Некоторые тесты не прошли. Проверьте конфигурацию.")
            
    except Exception as e:
        print(f"\n❌ Ошибка при запуске тестов агентов: {e}")
        print("💡 Убедитесь, что у вас есть файл .env с настройками Azure OpenAI")


if __name__ == "__main__":
    asyncio.run(main()) 