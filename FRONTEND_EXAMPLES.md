# ClosetMind Frontend - Примеры кода

## 🚀 JavaScript/TypeScript примеры для работы с API

### 📡 API Client Setup

```typescript
// api/client.ts
const API_BASE_URL = 'http://localhost:8000/api/v1';

class ClosetMindAPI {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  private async request(endpoint: string, options: RequestInit = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(this.token && { Authorization: `Bearer ${this.token}` }),
      ...options.headers,
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    return response.json();
  }

  // Chat methods
  async createChat(title: string) {
    return this.request('/chats/', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
  }

  async getChats() {
    return this.request('/chats/');
  }

  async getChatWithMessages(chatId: number) {
    return this.request(`/chats/${chatId}`);
  }

  async sendMessage(chatId: number, message: string) {
    return this.request(`/chats/${chatId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  }

  async deleteChat(chatId: number) {
    return this.request(`/chats/${chatId}`, {
      method: 'DELETE',
    });
  }
}

export const api = new ClosetMindAPI();
```

### 🎯 TypeScript Types

```typescript
// types/chat.ts
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

// Agent response types
export interface Product {
  name: string;
  price: string;
  description: string;
  link: string;
}

export interface ProductList {
  products: Product[];
}

export interface OutfitItem {
  name: string;
  category: string;
  image_url: string;
}

export interface Outfit {
  outfit_description: string;
  items: OutfitItem[];
  reasoning: string;
}

export interface GeneralResponse {
  response: string;
}

export type AgentResult = ProductList | Outfit | GeneralResponse;

export interface AgentResponse {
  result: AgentResult;
}
```

### 🔧 Utility Functions

```typescript
// utils/messageParser.ts
export function parseAgentMessage(content: string): AgentResponse {
  try {
    return JSON.parse(content);
  } catch (error) {
    console.error('Failed to parse agent message:', error);
    return {
      result: {
        response: 'Ошибка при обработке ответа'
      } as GeneralResponse
    };
  }
}

export function isProductList(result: AgentResult): result is ProductList {
  return 'products' in result;
}

export function isOutfit(result: AgentResult): result is Outfit {
  return 'outfit_description' in result && 'items' in result;
}

export function isGeneralResponse(result: AgentResult): result is GeneralResponse {
  return 'response' in result;
}
```

### 💬 React Components

#### Chat List Component
```tsx
// components/ChatList.tsx
import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { Chat } from '../types/chat';

export const ChatList: React.FC = () => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadChats();
  }, []);

  const loadChats = async () => {
    try {
      const data = await api.getChats();
      setChats(data);
    } catch (error) {
      console.error('Failed to load chats:', error);
    } finally {
      setLoading(false);
    }
  };

  const createNewChat = async () => {
    try {
      const newChat = await api.createChat('Новый чат');
      setChats([newChat, ...chats]);
    } catch (error) {
      console.error('Failed to create chat:', error);
    }
  };

  if (loading) return <div>Загрузка...</div>;

  return (
    <div className="chat-list">
      <button onClick={createNewChat} className="create-chat-btn">
        + Новый чат
      </button>
      {chats.map(chat => (
        <div key={chat.id} className="chat-item">
          <h3>{chat.title}</h3>
          <span>{new Date(chat.updated_at).toLocaleDateString()}</span>
        </div>
      ))}
    </div>
  );
};
```

#### Message Component
```tsx
// components/Message.tsx
import React from 'react';
import { Message as MessageType } from '../types/chat';
import { parseAgentMessage, isProductList, isOutfit, isGeneralResponse } from '../utils/messageParser';
import { ProductCard } from './ProductCard';
import { OutfitDisplay } from './OutfitDisplay';

interface MessageProps {
  message: MessageType;
}

export const Message: React.FC<MessageProps> = ({ message }) => {
  if (message.role === 'user') {
    return (
      <div className="message user-message">
        <div className="message-content">{message.content}</div>
      </div>
    );
  }

  // Parse assistant message
  const agentResponse = parseAgentMessage(message.content);
  const { result } = agentResponse;

  return (
    <div className="message assistant-message">
      {isProductList(result) && (
        <div className="products-grid">
          {result.products.map((product, index) => (
            <ProductCard key={index} product={product} />
          ))}
        </div>
      )}

      {isOutfit(result) && (
        <OutfitDisplay outfit={result} />
      )}

      {isGeneralResponse(result) && (
        <div className="general-response">
          {result.response}
        </div>
      )}
    </div>
  );
};
```

#### Product Card Component
```tsx
// components/ProductCard.tsx
import React from 'react';
import { Product } from '../types/chat';

interface ProductCardProps {
  product: Product;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  return (
    <div className="product-card">
      <h3 className="product-name">{product.name}</h3>
      <p className="product-price">{product.price}</p>
      <p className="product-description">{product.description}</p>
      <a 
        href={product.link} 
        target="_blank" 
        rel="noopener noreferrer"
        className="product-link"
      >
        Перейти в магазин
      </a>
    </div>
  );
};
```

#### Outfit Display Component
```tsx
// components/OutfitDisplay.tsx
import React from 'react';
import { Outfit } from '../types/chat';

interface OutfitDisplayProps {
  outfit: Outfit;
}

export const OutfitDisplay: React.FC<OutfitDisplayProps> = ({ outfit }) => {
  return (
    <div className="outfit-display">
      <h3 className="outfit-title">{outfit.outfit_description}</h3>
      
      <div className="outfit-items">
        {outfit.items.map((item, index) => (
          <div key={index} className="outfit-item">
            <img 
              src={item.image_url} 
              alt={item.name}
              className="outfit-item-image"
            />
            <div className="outfit-item-info">
              <h4>{item.name}</h4>
              <span className="category">{item.category}</span>
            </div>
          </div>
        ))}
      </div>
      
      <div className="outfit-reasoning">
        <h4>Почему этот образ работает:</h4>
        <p>{outfit.reasoning}</p>
      </div>
    </div>
  );
};
```

#### Chat Window Component
```tsx
// components/ChatWindow.tsx
import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';
import { ChatWithMessages, Message as MessageType } from '../types/chat';
import { Message } from './Message';

interface ChatWindowProps {
  chatId: number;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ chatId }) => {
  const [chat, setChat] = useState<ChatWithMessages | null>(null);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadChat();
  }, [chatId]);

  useEffect(() => {
    scrollToBottom();
  }, [chat?.messages]);

  const loadChat = async () => {
    try {
      const data = await api.getChatWithMessages(chatId);
      setChat(data);
    } catch (error) {
      console.error('Failed to load chat:', error);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || sending) return;

    setSending(true);
    try {
      const response = await api.sendMessage(chatId, newMessage);
      
      // Add user message and AI response to local state
      const userMessage: MessageType = {
        id: Date.now(), // temporary ID
        content: newMessage,
        role: 'user',
        chat_id: chatId,
        created_at: new Date().toISOString(),
      };

      setChat(prev => prev ? {
        ...prev,
        messages: [...prev.messages, userMessage, response]
      } : null);

      setNewMessage('');
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setSending(false);
    }
  };

  if (!chat) return <div>Загрузка...</div>;

  return (
    <div className="chat-window">
      <div className="chat-header">
        <h2>{chat.title}</h2>
      </div>

      <div className="messages-container">
        {chat.messages.map(message => (
          <Message key={message.id} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={sendMessage} className="message-form">
        <input
          type="text"
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          placeholder="Введите сообщение..."
          disabled={sending}
          className="message-input"
        />
        <button 
          type="submit" 
          disabled={sending || !newMessage.trim()}
          className="send-button"
        >
          {sending ? 'Отправка...' : 'Отправить'}
        </button>
      </form>
    </div>
  );
};
```

### 🎨 CSS Styles

```css
/* styles/chat.css */
.chat-list {
  width: 300px;
  border-right: 1px solid #e1e5e9;
  padding: 20px;
}

.create-chat-btn {
  width: 100%;
  padding: 12px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 8px;
  margin-bottom: 20px;
  cursor: pointer;
}

.chat-item {
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.chat-item:hover {
  background-color: #f8f9fa;
}

.chat-window {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.message {
  margin-bottom: 16px;
  max-width: 80%;
}

.user-message {
  margin-left: auto;
  background: #007bff;
  color: white;
  padding: 12px;
  border-radius: 18px;
}

.assistant-message {
  background: #f8f9fa;
  padding: 16px;
  border-radius: 12px;
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.product-card {
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  padding: 16px;
  background: white;
}

.product-link {
  display: inline-block;
  margin-top: 12px;
  padding: 8px 16px;
  background: #28a745;
  color: white;
  text-decoration: none;
  border-radius: 4px;
}

.outfit-display {
  background: white;
  border-radius: 12px;
  padding: 20px;
}

.outfit-items {
  display: flex;
  gap: 16px;
  margin: 16px 0;
  flex-wrap: wrap;
}

.outfit-item {
  text-align: center;
  flex: 1;
  min-width: 120px;
}

.outfit-item-image {
  width: 100px;
  height: 100px;
  object-fit: cover;
  border-radius: 8px;
}

.message-form {
  display: flex;
  padding: 20px;
  border-top: 1px solid #e1e5e9;
}

.message-input {
  flex: 1;
  padding: 12px;
  border: 1px solid #e1e5e9;
  border-radius: 24px;
  margin-right: 12px;
}

.send-button {
  padding: 12px 24px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 24px;
  cursor: pointer;
}
```

### 🔄 Usage Example

```tsx
// App.tsx
import React, { useState } from 'react';
import { ChatList } from './components/ChatList';
import { ChatWindow } from './components/ChatWindow';
import { api } from './api/client';

function App() {
  const [selectedChatId, setSelectedChatId] = useState<number | null>(null);

  // Set auth token (получить из localStorage или context)
  React.useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      api.setToken(token);
    }
  }, []);

  return (
    <div className="app">
      <ChatList onChatSelect={setSelectedChatId} />
      {selectedChatId && <ChatWindow chatId={selectedChatId} />}
    </div>
  );
}

export default App;
```

### 📱 Mobile Responsive

```css
/* styles/mobile.css */
@media (max-width: 768px) {
  .app {
    flex-direction: column;
  }
  
  .chat-list {
    width: 100%;
    height: 200px;
    overflow-y: auto;
  }
  
  .products-grid {
    grid-template-columns: 1fr;
  }
  
  .outfit-items {
    justify-content: center;
  }
  
  .message {
    max-width: 95%;
  }
}
```

Этот код предоставляет полный набор компонентов для работы с ClosetMind Chat API! 🚀 