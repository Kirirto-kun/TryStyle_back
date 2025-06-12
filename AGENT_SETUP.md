# ClosetMind Multi-Agent System Setup

## Обзор системы

Система состоит из мультиагентной архитектуры на базе Google ADK:

### **CoordinatorAgent** (Координирующий агент)
Главный агент, который анализирует запросы и передает их соответствующим sub-агентам.

### **SearchProcessingAgent** (Агент поиска и обработки)
Последовательный агент (SequentialAgent) из 4 шагов:

1. **SearchAgent** - Ищет данные в интернете через Google Search или Google Lens
2. **ScrapingAgent** - Скраппит полученные ссылки с помощью `utils/scrap_website.py` 
3. **ExtractionAgent** - Извлекает ключевые элементы (название, цена, ссылка) используя LLM
4. **ResponseAgent** - Форматирует финальный ответ для пользователя

### **GeneralQueryAgent** (Агент общих запросов)
Простой агент, который отвечает на общие вопросы пользователя.

## Настройка окружения

1. Создайте файл `.env` в корне проекта со следующими переменными:

```env
# Google ADK Configuration
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=ваш_google_api_key

# Для Google Search/Lens
GOOGLE_SERPER_API_KEY=ваш_serper_api_key
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Получение API ключей

### Google API Key
1. Перейдите на [Google AI Studio](https://aistudio.google.com/)
2. Создайте новый API ключ
3. Добавьте его в `.env` файл как `GOOGLE_API_KEY`

### Google Serper API Key
1. Перейдите на [Serper.dev](https://serper.dev/)
2. Зарегистрируйтесь и получите API ключ
3. Добавьте его в `.env` файл как `GOOGLE_SERPER_API_KEY`

## Запуск системы

### Через ADK CLI (рекомендуется для разработки)

**Терминальный интерфейс:**
```bash
cd src/agent
adk run .
```

**Веб-интерфейс ADK:**
```bash
cd src/agent  
adk web
```
Затем откройте http://localhost:8000 в браузере

### Через FastAPI
```bash
uvicorn src.main:app --reload
```

Затем отправьте POST запрос на `http://localhost:8000/api/v1/agent/chat`:

```json
{
    "message": "Найди информацию о iPhone 15 Pro"
}
```

## Примеры запросов

### Для поиска товаров/информации в интернете:
- "Найди информацию о iPhone 15 Pro"
- "Поищи цены на MacBook Air M2"
- "Найди обзоры Tesla Model 3"
- "Где купить Samsung Galaxy S24"

### Для общих вопросов:
- "Привет, как дела?"
- "Что такое искусственный интеллект?"
- "Расскажи анекдот"

## Структура файлов

```
src/
├── agent/
│   ├── __init__.py           # ADK module initialization
│   ├── agent.py              # Основные агенты для ADK CLI
│   └── agents.py             # Логика агентов для FastAPI интеграции
├── utils/
│   ├── google_search.py      # Функции для Google Search и Google Lens
│   └── scrap_website.py      # Функции для скраппинга сайтов
├── routers/
│   └── agent_router.py       # FastAPI роутер для агентов
└── main.py                   # Основное приложение FastAPI
```

## Как работает система

### В ADK CLI режиме:
1. CoordinatorAgent получает запрос пользователя
2. Анализирует его и определяет тип запроса
3. Передает запрос соответствующему sub-agent:
   - SearchProcessingAgent - для поиска в интернете
   - GeneralQueryAgent - для общих вопросов
4. Sub-agent обрабатывает запрос и возвращает результат

### В FastAPI режиме:
1. Пользователь отправляет запрос через API
2. Система определяет тип запроса по ключевым словам
3. Возвращает соответствующий ответ

## Архитектура агентов

```
CoordinatorAgent (root_agent)
├── SearchProcessingAgent (SequentialAgent)
│   ├── SearchAgent (с tools: search_web, search_by_image)
│   ├── ScrapingAgent (с tool: scrape_websites) 
│   ├── ExtractionAgent (с tool: extract_key_info)
│   └── ResponseAgent (форматирование)
└── GeneralQueryAgent (простые ответы)
```

## Возможные проблемы и решения

1. **Ошибка импорта google.adk**: Убедитесь, что установлен `google-adk==1.2.1`
2. **Ошибка API ключей**: Проверьте правильность ключей в `.env` файле
3. **Проблемы со скраппингом**: Убедитесь, что установлен `crawl4ai` и его зависимости
4. **ADK не видит агентов**: Убедитесь, что запускаете `adk` команды из папки `src/agent`

## Дополнительная настройка

Для использования Vertex AI вместо Google AI Studio, измените в `.env`:
```env
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=ваш_project_id
GOOGLE_CLOUD_LOCATION=us-central1
```

И настройте аутентификацию в Google Cloud:
```bash
gcloud auth application-default login
```

## Тестирование через ADK Web UI

1. Запустите `adk web` из папки `src/agent`
2. Откройте http://localhost:8000
3. Выберите "CoordinatorAgent" в dropdown
4. Тестируйте различные запросы:
   - "Найди цены на iPhone" (должен передать SearchProcessingAgent)
   - "Привет" (должен передать GeneralQueryAgent)

Система автоматически определит тип запроса и передаст его соответствующему агенту! 