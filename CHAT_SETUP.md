# Chat System Setup

## Что было добавлено

1. **Модели базы данных:**
   - `src/models/chat.py` - модели Chat и Message
   - Обновлен `src/models/user.py` - добавлена связь с чатами

2. **Схемы Pydantic:**
   - `src/schemas/chat.py` - схемы для API

3. **API роутер:**
   - `src/routers/chat.py` - эндпоинты для работы с чатами

4. **Миграция базы данных:**
   - `alembic/versions/001_add_chat_and_message_tables.py`

5. **Документация:**
   - `CHAT_API_USAGE.md` - документация по API

## Структура базы данных

### Таблица `chats`
- `id` - Primary Key
- `title` - Название чата
- `user_id` - Foreign Key на users
- `created_at` - Время создания
- `updated_at` - Время последнего обновления

### Таблица `messages`
- `id` - Primary Key  
- `content` - Содержимое сообщения
- `role` - Роль (user/assistant)
- `chat_id` - Foreign Key на chats
- `created_at` - Время создания

## Запуск с Docker

Если используете Docker:

```bash
# Запуск базы данных и приложения
docker-compose up -d

# Миграции выполнятся автоматически при создании таблиц
```

## Запуск локально

Если запускаете локально без Docker:

1. **Настройте переменные окружения:**
```bash
# Создайте .env файл
DATABASE_URL=postgresql://username:password@localhost:5432/dbname
```

2. **Активируйте виртуальное окружение:**
```bash
source venv/bin/activate
```

3. **Запустите приложение:**
```bash
python -m uvicorn src.main:app --reload
```

## Использование API

Полная документация API доступна в файле `CHAT_API_USAGE.md`.

### Быстрый пример:

1. **Создайте чат:**
```bash
curl -X POST "http://localhost:8000/api/v1/chats/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Fashion Chat"}'
```

2. **Отправьте сообщение:**
```bash
curl -X POST "http://localhost:8000/api/v1/chats/1/messages" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, I need fashion advice!"}'
```

3. **Получите историю чата:**
```bash
curl -X GET "http://localhost:8000/api/v1/chats/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Возможности системы

- ✅ Создание новых чатов с названием
- ✅ Получение списка всех чатов пользователя
- ✅ Получение конкретного чата с историей сообщений
- ✅ Отправка сообщений в чат с ответом от AI агента
- ✅ Удаление чатов
- ✅ Автоматическое сохранение истории сообщений
- ✅ Аутентификация пользователей
- ✅ Связь с существующей системой AI агентов

## Особенности реализации

1. **Безопасность:** Все операции требуют аутентификации
2. **Изоляция данных:** Пользователи видят только свои чаты
3. **Автоматическое обновление:** При добавлении сообщения обновляется `updated_at` чата
4. **Каскадное удаление:** При удалении чата удаляются все сообщения
5. **Интеграция с AI:** Сообщения автоматически обрабатываются системой агентов
6. **Контекст пользователя:** AI агент получает информацию о пользователе и чате 