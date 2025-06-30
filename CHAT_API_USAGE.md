# 💬 ClosetMind Chat API - Полная документация

## 📋 Оглавление
1. [🎯 Обзор системы](#обзор-системы)
2. [🏗️ Архитектура](#архитектура)
3. [🔐 Аутентификация](#аутентификация)
4. [📡 API Endpoints](#api-endpoints)
5. [🤖 Система агентов](#система-агентов)
6. [📊 Структуры данных](#структуры-данных)
7. [💻 Техническое задание для фронтенда](#техническое-задание-для-фронтенда)
8. [🔧 Примеры кода](#примеры-кода)
9. [⚠️ Обработка ошибок](#обработка-ошибок)
10. [🚀 Лучшие практики](#лучшие-практики)

---

## 🎯 Обзор системы

**ClosetMind Chat** - это интеллектуальная система чата с поддержкой AI-агентов для работы с модой и гардеробом. Система использует многоагентную архитектуру на базе **PydanticAI** для обработки различных типов запросов пользователей.

### ✨ Основные возможности:
- 💬 Создание и управление чатами
- 🤖 3 специализированных AI-агента
- 🔍 Поиск товаров в интернете
- 👗 Рекомендации нарядов
- 💾 Сохранение истории сообщений
- 🔐 Полная безопасность и изоляция данных
- 📱 Готовность к мобильным приложениям

---

## 🏗️ Архитектура

### Компоненты системы:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Chat API      │    │   AI Agents     │
│   (React/Vue)   │◄──►│   (FastAPI)     │◄──►│   (PydanticAI)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   PostgreSQL    │
                       │   Database      │
                       └─────────────────┘
```

### База данных:

**Таблица `chats`:**
- `id` (Primary Key)
- `title` - Название чата
- `user_id` (Foreign Key) - ID пользователя
- `created_at` - Время создания
- `updated_at` - Время последнего обновления

**Таблица `messages`:**
- `id` (Primary Key)
- `content` - Содержимое сообщения
- `role` - Роль (`user` или `assistant`)
- `chat_id` (Foreign Key) - ID чата
- `created_at` - Время создания

---

## 🔐 Аутентификация

**Все запросы требуют JWT токен в заголовке:**

```http
Authorization: Bearer <your_jwt_token>
```

**Получение токена:**
1. Пользователь регистрируется/входит через `/api/v1/auth/login`
2. Получает JWT токен
3. Использует токен для всех запросов к чату

---

## 📡 API Endpoints

### Base URL: `/api/v1/chats`


### 2. 📋 Получить все чаты пользователя

```http
GET /api/v1/chats/
```

**Response (200):**
```json
[
  {
    "id": 1,
    "title": "Поиск одежды",
    "user_id": 123,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T11:45:00Z"
  },
  {
    "id": 2,
    "title": "Стильные образы",
    "user_id": 123,
    "created_at": "2024-01-14T15:20:00Z",
    "updated_at": "2024-01-14T16:10:00Z"
  }
]
```

### 3. 💬 Получить чат с сообщениями

```http
GET /api/v1/chats/{chat_id}
```

**Response (200):**
```json
{
  "id": 1,
  "title": "Поиск одежды",
  "user_id": 123,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:45:00Z",
  "messages": [
    {
      "id": 1,
      "content": "Найди мне черную футболку",
      "role": "user",
      "chat_id": 1,
      "created_at": "2024-01-15T10:31:00Z"
    },
    {
      "id": 2,
      "content": "{\"result\": {\"products\": [...]}}",
      "role": "assistant",
      "chat_id": 1,
      "created_at": "2024-01-15T10:31:30Z"
    }
  ]
}
```

### 4. 📤 Отправить сообщение в чат

```http
POST /api/v1/chats/{chat_id}/messages
```

**Request Body:**
```json
{
  "message": "Найди мне красивое платье для свидания"
}
```

**Response (200):**
```json
{
  "id": 3,
  "content": "{\"result\": {\"products\": [...]}, \"agent_type\": \"search\", \"processing_time_ms\": 1245.6}",
  "role": "assistant",
  "chat_id": 1,
  "created_at": "2024-01-15T10:32:00Z"
}
```

### 5. 📨 Получить сообщения чата

```http
GET /api/v1/chats/{chat_id}/messages
```

**Response (200):**
```json
[
  {
    "id": 1,
    "content": "Что мне надеть сегодня?",
    "role": "user",
    "chat_id": 1,
    "created_at": "2024-01-15T10:31:00Z"
  },
  {
    "id": 2,
    "content": "{\"result\": {\"outfit_description\": \"Стильный образ для работы\"}}",
    "role": "assistant",
    "chat_id": 1,
    "created_at": "2024-01-15T10:31:30Z"
  }
]
```

### 6. 🗑️ Удалить чат

```http
DELETE /api/v1/chats/{chat_id}
```

**Response (200):**
```json
{
  "message": "Chat deleted successfully"
}
```

### 7. 🚀 Создать чат с первым сообщением

```http
POST /api/v1/chats/init
```

**Request Body:**
```json
{
  "message": "Привет! Помоги мне с модой"
}
```

**Response (201):**
```json
{
  "id": 4,
  "title": "Помощь с модой", // Автоматически сгенерированный заголовок
  "user_id": 123,
  "created_at": "2024-01-15T10:35:00Z",
  "updated_at": "2024-01-15T10:35:30Z",
  "messages": [
    {
      "id": 7,
      "content": "Привет! Помоги мне с модой",
      "role": "user",
      "chat_id": 4,
      "created_at": "2024-01-15T10:35:00Z"
    },
    {
      "id": 8,
      "content": "{\"result\": {\"response\": \"Привет! Я помогу тебе с модой!\"}}",
      "role": "assistant", 
      "chat_id": 4,
      "created_at": "2024-01-15T10:35:30Z"
    }
  ]
}
```

---

## 🤖 Система агентов

### Архитектура агентов:

```
User Message → Coordinator Agent → Specialized Agent → Structured Response
                      ↓
                ┌─────────────┐
                │ Determines  │
                │ Intent      │
                └─────────────┘
                      ↓
        ┌─────────────┬─────────────┬─────────────┐
        ▼             ▼             ▼
  Search Agent   Outfit Agent   General Agent
     (Поиск)      (Наряды)      (Общение)
```

### 1. 🔍 Search Agent (Поиск товаров)

**Триггеры:** "найди", "купить", "где купить", "поиск", "товар", "магазин", "стоимость"

**Функции:**
- Поиск товаров в интернете
- Анализ цен
- Подбор по категориям
- Фильтрация по бюджету

**Структура ответа:**
```json
{
  "result": {
    "products": [
      {
        "name": "Черная футболка Uniqlo",
        "price": "1299 ₽",
        "description": "Базовая хлопковая футболка, идеальна для повседневной носки",
        "link": "https://www.uniqlo.com/ru/products/..."
      }
    ]
  },
  "agent_type": "search",
  "processing_time_ms": 856.4
}
```

### 2. 👗 Outfit Agent (Рекомендации нарядов)

**Триггеры:** "что надеть", "образ", "наряд", "стиль", "гардероб", "одежда", "сочетание"

**Функции:**
- Подбор образов из гардероба
- Анализ стиля
- Рекомендации по событиям
- Объяснение выбора

**Структура ответа:**
```json
{
  "result": {
    "outfit_description": "Стильный повседневный образ для прогулки по городу",
    "items": [
      {
        "name": "Белая рубашка",
        "category": "Рубашки",
        "image_url": "https://example.com/shirt.jpg"
      },
      {
        "name": "Синие джинсы", 
        "category": "Брюки",
        "image_url": "https://example.com/jeans.jpg"
      }
    ],
    "reasoning": "Белый и синий - классическое сочетание, которое всегда выглядит стильно"
  },
  "agent_type": "outfit",
  "processing_time_ms": 1123.7
}
```

### 3. 💭 General Agent (Общие вопросы)

**Триггеры:** все остальные запросы

**Функции:**
- Общение на любые темы
- Советы по моде
- Информация о трендах
- Помощь по уходу за одеждой

**Структура ответа:**
```json
{
  "result": {
    "response": "Искусственный интеллект помогает создавать персонализированные рекомендации в сфере моды, анализируя ваши предпочтения и текущие тренды.",
    "response_type": "informational",
    "confidence": 0.95
  },
  "agent_type": "general",
  "processing_time_ms": 432.1
}
```

---

## 📊 Структуры данных

### TypeScript интерфейсы:

```typescript
// Базовые типы
export interface Chat {
  id: number;
  title: string;
  user_id: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  content: string;
  role: 'user' | 'assistant';
  chat_id: number;
  created_at: string;
}

export interface ChatWithMessages extends Chat {
  messages: Message[];
}

// Ответы агентов
export interface Product {
  name: string;
  price: string;
  description: string;
  link: string;
}

export interface ProductSearchResult {
  products: Product[];
}

export interface OutfitItem {
  name: string;
  category: string;
  image_url: string;
}

export interface OutfitRecommendation {
  outfit_description: string;
  items: OutfitItem[];
  reasoning: string;
}

export interface GeneralResponse {
  response: string;
  response_type?: string;
  confidence?: number;
}

export interface AgentResponse {
  result: ProductSearchResult | OutfitRecommendation | GeneralResponse;
  agent_type: 'search' | 'outfit' | 'general';
  processing_time_ms: number;
}
```

---

## 💻 Техническое задание для фронтенда

### 🎯 Основные требования

#### 1. Архитектура приложения
- **SPA** (Single Page Application) на React/Vue/Angular
- **State Management** (Redux/Vuex/Pinia) для управления состоянием чатов
- **Responsive Design** - поддержка мобильных устройств
- **PWA** готовность (опционально)

#### 2. Ключевые компоненты

```
App
├── ChatSidebar (список чатов)
├── ChatWindow (основное окно чата)
│   ├── ChatHeader (заголовок чата)
│   ├── MessagesList (список сообщений)
│   │   ├── UserMessage (сообщение пользователя)
│   │   └── AssistantMessage (ответ AI)
│   │       ├── ProductGrid (сетка товаров)
│   │       ├── OutfitDisplay (отображение образа)
│   │       └── GeneralResponse (текстовый ответ)
│   └── MessageInput (поле ввода)
└── AuthGuard (защита маршрутов)
```

#### 3. Страницы и маршруты

```typescript
// Роутинг
const routes = [
  { path: '/', component: Home },           // Главная страница
  { path: '/login', component: Login },     // Авторизация
  { path: '/chats', component: ChatApp },   // Приложение чата
  { path: '/chats/:id', component: ChatApp }, // Конкретный чат
  { path: '/profile', component: Profile }  // Профиль пользователя
];
```

#### 4. Функциональные требования

##### 🔐 Аутентификация
- [ ] Логин/регистрация
- [ ] Сохранение JWT токена
- [ ] Автоматическое обновление токена
- [ ] Выход из системы

##### 💬 Управление чатами
- [ ] Создание нового чата
- [ ] Список всех чатов пользователя
- [ ] Переключение между чатами
- [ ] Удаление чатов
- [ ] Поиск по чатам

##### 📨 Работа с сообщениями
- [ ] Отправка текстовых сообщений
- [ ] Отображение истории сообщений
- [ ] Автоскролл к новым сообщениям
- [ ] Статусы сообщений (отправляется/доставлено)
- [ ] Индикатор печатания

##### 🤖 Обработка ответов агентов
- [ ] Парсинг JSON ответов
- [ ] Определение типа агента
- [ ] Специализированное отображение:
  - **Товары** - карточки с изображениями, ценами, ссылками
  - **Наряды** - визуальные образы с описанием
  - **Общие ответы** - форматированный текст

#### 5. UI/UX требования

##### 🎨 Дизайн
- **Современный Material Design** или **минималистичный стиль**
- **Темная/светлая тема** (переключатель)
- **Анимации** для плавных переходов
- **Адаптивность** для всех устройств

##### 🔄 Интерактивность
- **Real-time** обновления (WebSocket опционально)
- **Drag & Drop** для файлов (будущая функция)
- **Keyboard shortcuts** (Ctrl+Enter для отправки)
- **Infinite scroll** для длинной истории

##### ⚡ Производительность
- **Lazy loading** сообщений
- **Виртуализация** для больших списков
- **Кэширование** данных
- **Optimistic updates** для лучшего UX

---

## 🔧 Примеры кода

### API Client

```typescript
// api/chatApi.ts
class ChatAPI {
  private baseURL = 'http://localhost:8000/api/v1';
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(this.token && { Authorization: `Bearer ${this.token}` }),
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  // Методы для работы с чатами
  async createChat(title: string): Promise<Chat> {
    return this.request('/chats/', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
  }

  async getChats(): Promise<Chat[]> {
    return this.request('/chats/');
  }

  async getChatWithMessages(chatId: number): Promise<ChatWithMessages> {
    return this.request(`/chats/${chatId}`);
  }

  async sendMessage(chatId: number, message: string): Promise<Message> {
    return this.request(`/chats/${chatId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  }

  async initChatWithMessage(message: string): Promise<ChatWithMessages> {
    return this.request('/chats/init', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  }

  async deleteChat(chatId: number): Promise<{ message: string }> {
    return this.request(`/chats/${chatId}`, {
      method: 'DELETE',
    });
  }
}

export const chatAPI = new ChatAPI();
```

### React Hooks

```typescript
// hooks/useChat.ts
import { useState, useEffect } from 'react';
import { chatAPI } from '../api/chatApi';

export const useChat = (chatId: number | null) => {
  const [chat, setChat] = useState<ChatWithMessages | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (chatId) {
      loadChat(chatId);
    }
  }, [chatId]);

  const loadChat = async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const chatData = await chatAPI.getChatWithMessages(id);
      setChat(chatData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки чата');
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (message: string) => {
    if (!chatId) return;
    
    try {
      // Optimistic update
      const tempMessage: Message = {
        id: Date.now(),
        content: message,
        role: 'user',
        chat_id: chatId,
        created_at: new Date().toISOString(),
      };

      setChat(prev => prev ? {
        ...prev,
        messages: [...prev.messages, tempMessage]
      } : null);

      const response = await chatAPI.sendMessage(chatId, message);
      
      // Обновляем с реальным ответом
      setChat(prev => prev ? {
        ...prev,
        messages: [
          ...prev.messages.slice(0, -1), // убираем временное сообщение
          { ...tempMessage, id: response.id - 1 }, // пользовательское сообщение
          response // ответ AI
        ]
      } : null);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка отправки сообщения');
      // Откатываем optimistic update
      setChat(prev => prev ? {
        ...prev,
        messages: prev.messages.slice(0, -1)
      } : null);
    }
  };

  return { chat, loading, error, sendMessage, reloadChat: () => chatId && loadChat(chatId) };
};
```

### Компонент отображения сообщений

```tsx
// components/MessageDisplay.tsx
import React from 'react';
import { Message } from '../types/chat';
import { parseAgentResponse } from '../utils/messageParser';
import { ProductGrid } from './ProductGrid';
import { OutfitDisplay } from './OutfitDisplay';

interface MessageDisplayProps {
  message: Message;
}

export const MessageDisplay: React.FC<MessageDisplayProps> = ({ message }) => {
  // Пользовательское сообщение
  if (message.role === 'user') {
    return (
      <div className="message user-message">
        <div className="message-bubble user-bubble">
          {message.content}
        </div>
        <div className="message-time">
          {new Date(message.created_at).toLocaleTimeString()}
        </div>
      </div>
    );
  }

  // Ответ ассистента
  const agentResponse = parseAgentResponse(message.content);
  
  return (
    <div className="message assistant-message">
      {/* Отображение в зависимости от типа агента */}
      {agentResponse.agent_type === 'search' && (
        <ProductGrid products={(agentResponse.result as ProductSearchResult).products} />
      )}
      
      {agentResponse.agent_type === 'outfit' && (
        <OutfitDisplay outfit={agentResponse.result as OutfitRecommendation} />
      )}
      
      {agentResponse.agent_type === 'general' && (
        <div className="general-response">
          <div className="response-text">
            {(agentResponse.result as GeneralResponse).response}
          </div>
        </div>
      )}
      
      {/* Метаинформация */}
      <div className="message-meta">
        <span className="agent-type">{agentResponse.agent_type}</span>
        <span className="processing-time">
          {agentResponse.processing_time_ms.toFixed(0)}ms
        </span>
        <span className="message-time">
          {new Date(message.created_at).toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
};
```

---

## ⚠️ Обработка ошибок

### Типы ошибок API

```typescript
interface APIError {
  detail: string;
  status_code: number;
}

// Распространенные ошибки
const errorMessages = {
  400: 'Неверный запрос',
  401: 'Необходима авторизация', 
  403: 'Доступ запрещен',
  404: 'Чат не найден',
  429: 'Слишком много запросов',
  500: 'Ошибка сервера'
};
```

### Обработка в компонентах

```tsx
// components/ErrorBoundary.tsx
import React, { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Chat error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-fallback">
          <h2>Что-то пошло не так 😞</h2>
          <p>Произошла ошибка в чате. Попробуйте обновить страницу.</p>
          <button onClick={() => window.location.reload()}>
            Обновить страницу
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
```

---

## 🚀 Лучшие практики

### 🔒 Безопасность
- **Никогда не храните токены в localStorage** - используйте httpOnly cookies
- **Валидируйте все пользовательские данные** на фронтенде
- **Реализуйте rate limiting** для отправки сообщений
- **Санитизируйте HTML** в сообщениях

### ⚡ Производительность  
- **Используйте React.memo** для предотвращения лишних рендеров
- **Виртуализируйте длинные списки** сообщений
- **Дебаунсируйте поиск** по чатам
- **Кэшируйте результаты** API запросов

### 🎨 UX
- **Показывайте статус загрузки** при отправке сообщений
- **Добавьте анимации** для появления новых сообщений
- **Реализуйте drag & drop** для будущих файловых вложений
- **Поддержите keyboard navigation**

### 🧪 Тестирование
```typescript
// Пример unit теста
import { render, screen, fireEvent } from '@testing-library/react';
import { MessageDisplay } from '../MessageDisplay';

test('отображает пользовательское сообщение', () => {
  const message = {
    id: 1,
    content: 'Тестовое сообщение',
    role: 'user' as const,
    chat_id: 1,
    created_at: '2024-01-15T10:30:00Z'
  };

  render(<MessageDisplay message={message} />);
  
  expect(screen.getByText('Тестовое сообщение')).toBeInTheDocument();
  expect(screen.getByText(/10:30/)).toBeInTheDocument();
});
```

---

## 📚 Дополнительные ресурсы

- **API документация**: [FRONTEND_API_DOCUMENTATION.md](./FRONTEND_API_DOCUMENTATION.md)
- **Примеры кода**: [FRONTEND_EXAMPLES.md](./FRONTEND_EXAMPLES.md)
- **Настройка агентов**: [AGENT_SETUP.md](./AGENT_SETUP.md)
- **Быстрый старт**: [QUICK_START.md](./QUICK_START.md)

---

## 🆘 Поддержка

При возникновении проблем:

1. **Проверьте логи браузера** на наличие ошибок
2. **Убедитесь в валидности токена** авторизации
3. **Проверьте статус сервера** (должен быть запущен на порту 8000)
4. **Изучите документацию API** для правильного формата запросов

**Контакты для технической поддержки:**
- 📧 Email: dev@closetmind.ai
- 💬 Slack: #closetmind-support
- 📖 Wiki: [github.com/closetmind/docs](https://github.com/closetmind/docs)

---

*Документация обновлена: 15 января 2024*
