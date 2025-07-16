# API эндпоинты для админа магазина

## 🔐 **Авторизация**
Все эндпоинты требуют Bearer Token с ролью `STORE_ADMIN` или `ADMIN`

## 📊 **Главный дашборд**
```bash
GET /api/v1/store-admin/dashboard
```
**Возвращает:**
- Статистика товаров (всего/активных/неактивных)
- Товары по категориям  
- Статистика отзывов и рейтинг
- Последние добавленные товары (5 шт)
- Товары с низким остатком (≤5 шт)
- Топ товары по рейтингу

**Пример ответа:**
```json
{
  "store": {
    "id": 1,
    "name": "H&M",
    "city": "Алматы",
    "logo_url": "https://...",
    "rating": 4.5
  },
  "total_products": 150,
  "active_products": 140,
  "inactive_products": 10,
  "products_by_category": {
    "рубашки": 45,
    "джинсы": 30,
    "платья": 25
  },
  "total_reviews": 1250,
  "average_rating": 4.2,
  "recent_products": [...],
  "low_stock_products": [...],
  "top_rated_products": [...]
}
```

## 🛍️ **Управление товарами**

### **Просмотр всех товаров магазина**
```bash
GET /api/v1/store-admin/products
```
**Параметры:**
- `category` - фильтр по категории
- `in_stock_only` - только товары в наличии (true/false)
- `sort_by` - сортировка: name, price, rating, created_at, stock_quantity
- `sort_order` - порядок: asc, desc
- `page` - номер страницы (по умолчанию 1)
- `per_page` - товаров на странице (по умолчанию 20, макс 100)

**Примеры запросов:**
```bash
# Все товары
GET /api/v1/store-admin/products

# Только рубашки в наличии, отсортированные по цене
GET /api/v1/store-admin/products?category=рубашки&in_stock_only=true&sort_by=price&sort_order=asc

# Вторая страница, по 50 товаров
GET /api/v1/store-admin/products?page=2&per_page=50

# Товары с низким остатком
GET /api/v1/store-admin/products?sort_by=stock_quantity&sort_order=asc
```

**Пример ответа:**
```json
{
  "products": [
    {
      "id": 123,
      "name": "Рубашка белая классическая",
      "price": 15000,
      "original_price": 18000,
      "rating": 4.5,
      "image_urls": ["https://..."],
      "discount_percentage": 17,
      "is_in_stock": true,
      "store": {
        "id": 1,
        "name": "H&M",
        "city": "Алматы",
        "logo_url": "https://...",
        "rating": 4.5
      }
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 20,
  "filters": {
    "category": "рубашки",
    "in_stock_only": true
  }
}
```

### **Создать товар**
```bash
POST /api/v1/store-admin/products
```
**Тело запроса:**
```json
{
  "name": "Рубашка белая классическая",
  "description": "Классическая белая рубашка из хлопка",
  "price": 15000,
  "original_price": 18000,
  "category": "рубашки",
  "brand": "H&M",
  "sizes": ["S", "M", "L", "XL"],
  "colors": ["белый"],
  "image_urls": ["https://firebase.com/image1.jpg"],
  "stock_quantity": 10,
  "is_active": true
}
```

**Обязательные поля:**
- `name` - название товара
- `price` - цена (> 0)
- `category` - категория
- `stock_quantity` - количество (≥ 0)

**Опциональные поля:**
- `description` - описание
- `original_price` - цена до скидки
- `brand` - бренд
- `sizes` - размеры
- `colors` - цвета
- `image_urls` - изображения
- `is_active` - активность (по умолчанию true)

### **Обновить товар**
```bash
PUT /api/v1/store-admin/products/{product_id}
```
**Можно обновлять частично** - любые поля из схемы создания

**Пример:**
```json
{
  "price": 14000,
  "stock_quantity": 5,
  "is_active": false
}
```

### **Удалить товар**
```bash
DELETE /api/v1/store-admin/products/{product_id}
```

## 📸 **Создание товара через фото (AI анализ)**
```bash
POST /api/v1/store-admin/products/upload-photos
```
**Тело запроса:**
```json
{
  "images_base64": [
    "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD...",
    "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD..."
  ],
  "name": "Рубашка красивая",
  "price": 15000,
  "original_price": 18000,
  "sizes": ["S", "M", "L"],
  "colors": ["синий", "белый"],
  "stock_quantity": 5
}
```

**Обязательные поля:**
- `images_base64` - массив base64 изображений (1-5 фото)
- `price` - цена товара

**Опциональные поля:**
- `name` - название (если не указано, AI сгенерирует)
- `original_price` - цена до скидки
- `sizes` - размеры
- `colors` - цвета  
- `stock_quantity` - количество на складе

**AI автоматически определит:**
- ✅ Категорию товара
- ✅ Описание
- ✅ Характеристики и особенности
- ✅ Название (если не указано)
- ✅ Загрузит изображения в Firebase

**Валидация изображений:**
- Формат: data:image/jpeg или data:image/png
- Максимум 5 изображений за раз
- Максимальный размер: 10MB на изображение

## 📈 **Аналитика**
```bash
GET /api/v1/store-admin/analytics?period=month
```
**Параметры:**
- `period` - период анализа:
  - `week` - неделя
  - `month` - месяц (по умолчанию)
  - `year` - год

**Возвращает:**
```json
{
  "period": "month",
  "products_added": 25,
  "reviews_received": 150,
  "rating_change": 0.2,
  "period_start": "2025-01-01T00:00:00Z",
  "period_end": "2025-01-31T23:59:59Z"
}
```

## 🔔 **Уведомления о низком остатке**
```bash
GET /api/v1/store-admin/low-stock-alerts?threshold=5
```
**Параметры:**
- `threshold` - порог для уведомления (по умолчанию 5)

**Возвращает список товаров с остатком ≤ threshold:**
```json
[
  {
    "product_id": 123,
    "product_name": "Рубашка белая",
    "current_stock": 2,
    "threshold": 5,
    "category": "рубашки"
  },
  {
    "product_id": 124,
    "product_name": "Джинсы синие",
    "current_stock": 1,
    "threshold": 5,
    "category": "джинсы"
  }
]
```

## ⚙️ **Настройки магазина**
```bash
PUT /api/v1/store-admin/store-settings
```
**Тело запроса:**
```json
{
  "name": "H&M Updated",
  "description": "Модная одежда для всех возрастов",
  "city": "Алматы", 
  "logo_url": "https://firebase.com/logo.jpg",
  "website_url": "https://hm.kz"
}
```

**Все поля опциональные** - можно обновлять частично.

## 📄 **Примеры использования**

### **1. Авторизация**
```bash
# Получить токен
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@hm.kz&password=admin123"

# Ответ
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### **2. Получить дашборд**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/store-admin/dashboard
```

### **3. Получить все товары**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/store-admin/products
```

### **4. Фильтрация товаров**
```bash
# Только товары в наличии, отсортированные по цене
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/store-admin/products?in_stock_only=true&sort_by=price&sort_order=asc"

# По категории "рубашки", вторая страница
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/store-admin/products?category=рубашки&page=2&per_page=10"

# Товары с низким остатком
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/store-admin/products?sort_by=stock_quantity&sort_order=asc&per_page=5"
```

### **5. Создать товар**
```bash
curl -X POST http://localhost:8000/api/v1/store-admin/products \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Джинсы синие классические",
    "description": "Удобные джинсы из денима",
    "price": 12000,
    "original_price": 15000,
    "category": "джинсы",
    "brand": "Levi'\''s",
    "sizes": ["30", "32", "34", "36"],
    "colors": ["синий", "черный"],
    "stock_quantity": 15
  }'
```

### **6. Обновить товар**
```bash
curl -X PUT http://localhost:8000/api/v1/store-admin/products/123 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "price": 11000,
    "stock_quantity": 8
  }'
```

### **7. Создать товар через фото**
```bash
curl -X POST http://localhost:8000/api/v1/store-admin/products/upload-photos \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "images_base64": ["data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD..."],
    "price": 18000,
    "sizes": ["S", "M", "L"],
    "colors": ["красный"],
    "stock_quantity": 10
  }'
```

### **8. Получить уведомления о низком остатке**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/store-admin/low-stock-alerts?threshold=3"
```

### **9. Получить аналитику**
```bash
# За неделю
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/store-admin/analytics?period=week"

# За год
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/store-admin/analytics?period=year"
```

### **10. Обновить настройки магазина**
```bash
curl -X PUT http://localhost:8000/api/v1/store-admin/store-settings \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "H&M Kazakhstan",
    "description": "Стильная одежда для всей семьи",
    "website_url": "https://hm.kz"
  }'
```

## 🔒 **Безопасность и права доступа**

### **Для STORE_ADMIN:**
- ✅ Видит только товары **своего** магазина
- ✅ Может управлять только **своими** товарами
- ✅ Может изменять настройки **своего** магазина
- ❌ Не может видеть товары других магазинов
- ❌ Не может создавать новые магазины

### **Для ADMIN (суперадмин):**
- ✅ Имеет доступ ко **всем** магазинам
- ✅ Может управлять товарами **любого** магазина
- ✅ Может создавать новые магазины
- ✅ Может назначать админов магазинов

### **Логирование:**
Все действия админов магазинов логируются:
```
Store admin username created product: Product Name in store Store Name
Store admin username updated product: Product Name  
Store admin username updated store settings for Store Name
```

## ❌ **Коды ошибок**

| Код | Описание | Причина |
|-----|----------|---------|
| 400 | Bad Request | Некорректные данные запроса |
| 401 | Unauthorized | Не авторизован или токен недействителен |
| 403 | Forbidden | Недостаточно прав (не админ магазина) |
| 404 | Not Found | Товар, магазин или ресурс не найден |
| 422 | Validation Error | Ошибка валидации данных |
| 500 | Internal Server Error | Внутренняя ошибка сервера |

## 📝 **Дополнительная информация**

### **Особенности работы:**
- Если вы **суперадмин** (роль ADMIN), система пока берет первый доступный магазин
- Все эндпоинты возвращают полную информацию о товарах с данными о магазине
- Поддерживается пагинация для больших списков товаров
- AI анализ фотографий работает автоматически при загрузке
- Изображения автоматически загружаются в Firebase Storage

### **Рекомендации:**
- Используйте фильтрацию для больших каталогов товаров
- Регулярно проверяйте уведомления о низком остатке
- Используйте AI загрузку для быстрого добавления товаров
- Следите за аналитикой для понимания тенденций

### **Создание тестового админа:**
Если у вас еще нет админа магазина:
```bash
# Автоматическое создание
python scripts/create_store_admin.py

# Интерактивное создание
python scripts/create_store_admin.py --interactive

# Создание через API (требует суперадмина)
POST /api/v1/admin/create-store-admin
```

**Это полный набор API эндпоинтов для админа магазина! 🎯** 