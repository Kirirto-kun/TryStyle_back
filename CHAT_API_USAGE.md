# Chat API Usage

This document describes how to use the Chat API endpoints.

## Authentication

All chat endpoints require authentication. Include the Bearer token in the Authorization header:

```
Authorization: Bearer <your_access_token>
```

## Endpoints

### 1. Create a new chat

**POST** `/api/v1/chats/`

**Request Body:**
```json
{
  "title": "My Fashion Chat"
}
```

**Response:**
```json
{
  "id": 1,
  "title": "My Fashion Chat",
  "user_id": 1,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": null
}
```

### 2. Get all chats for current user

**GET** `/api/v1/chats/`

**Response:**
```json
[
  {
    "id": 1,
    "title": "My Fashion Chat",
    "user_id": 1,
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:30:00Z"
  }
]
```

### 3. Get a specific chat with messages

**GET** `/api/v1/chats/{chat_id}`

**Response:**
```json
{
  "id": 1,
  "title": "My Fashion Chat",
  "user_id": 1,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:30:00Z",
  "messages": [
    {
      "id": 1,
      "content": "Hello, I need help with my outfit",
      "role": "user",
      "chat_id": 1,
      "created_at": "2024-01-01T12:01:00Z"
    },
    {
      "id": 2,
      "content": "I'd be happy to help! What kind of outfit are you looking for?",
      "role": "assistant",
      "chat_id": 1,
      "created_at": "2024-01-01T12:01:05Z"
    }
  ]
}
```

### 4. Send a message to a chat

**POST** `/api/v1/chats/{chat_id}/messages`

**Request Body:**
```json
{
  "message": "I need a casual outfit for a weekend trip"
}
```

**Response:**
```json
{
  "id": 3,
  "content": "For a casual weekend trip, I recommend...",
  "role": "assistant",
  "chat_id": 1,
  "created_at": "2024-01-01T12:05:00Z"
}
```

### 5. Get messages from a specific chat

**GET** `/api/v1/chats/{chat_id}/messages`

**Response:**
```json
[
  {
    "id": 1,
    "content": "Hello, I need help with my outfit",
    "role": "user",
    "chat_id": 1,
    "created_at": "2024-01-01T12:01:00Z"
  },
  {
    "id": 2,
    "content": "I'd be happy to help! What kind of outfit are you looking for?",
    "role": "assistant",
    "chat_id": 1,
    "created_at": "2024-01-01T12:01:05Z"
  }
]
```

### 6. Delete a chat

**DELETE** `/api/v1/chats/{chat_id}`

**Response:**
```json
{
  "message": "Chat deleted successfully"
}
```

## Usage Flow

1. **Register/Login** to get an access token
2. **Create a chat** with a meaningful title
3. **Send messages** to the chat to interact with the AI agent
4. **Retrieve chat history** to continue conversations
5. **Delete chats** when no longer needed

## Error Responses

- **401 Unauthorized**: Invalid or missing token
- **404 Not Found**: Chat not found or doesn't belong to user
- **500 Internal Server Error**: Server error during message processing

## Notes

- Chat messages are processed through the AI agent system
- User context (User ID, Chat ID) is automatically included in agent processing
- Chat `updated_at` timestamp is updated when new messages are added
- Deleting a chat removes all its messages (cascade delete) 