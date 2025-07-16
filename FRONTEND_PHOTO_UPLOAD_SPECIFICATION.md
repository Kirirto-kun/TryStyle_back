# Техническое задание: Добавление товаров через фото (Frontend)

## Обзор функциональности

Админы магазинов могут добавлять товары в каталог через загрузку фотографий с автоматическим AI анализом характеристик одежды.

## API Endpoint

**URL:** `POST /api/v1/store-admin/products/upload-photos`  
**Авторизация:** Bearer Token (роль STORE_ADMIN или ADMIN)  
**Content-Type:** `application/json`

## Структура запроса

```typescript
interface PhotoProductUpload {
  images_base64: string[];           // Массив base64 изображений (1-5 фото)
  name?: string;                     // Название товара (опционально)
  price: number;                     // Цена товара в тенге
  original_price?: number;           // Цена до скидки (опционально)
  sizes: string[];                   // Размеры ["S", "M", "L", "XL"]
  colors: string[];                  // Цвета ["белый", "черный", "синий"]
  stock_quantity: number;            // Количество на складе
}
```

## Структура ответа

```typescript
interface ProductResponse {
  id: number;
  name: string;
  description: string;
  price: number;
  original_price?: number;
  category: string;
  brand: string;                     // Название магазина
  features: string[];                // Характеристики от AI
  sizes: string[];
  colors: string[];
  image_urls: string[];              // URL изображений в Firebase
  stock_quantity: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  store_id: number;
  
  // Вычисляемые поля
  price_info: {
    formatted_price: string;
    formatted_original_price?: string;
  };
  discount_percentage: number;
  is_in_stock: boolean;
  
  store: {
    id: number;
    name: string;
    city: string;
    logo_url?: string;
    rating: number;
  };
}
```

## Примеры кода

### 1. Базовый JavaScript API Client

```javascript
class ProductPhotoAPI {
  constructor(baseURL, authToken) {
    this.baseURL = baseURL;
    this.authToken = authToken;
  }

  async uploadProductPhotos(productData) {
    const response = await fetch(`${this.baseURL}/api/v1/store-admin/products/upload-photos`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.authToken}`
      },
      body: JSON.stringify(productData)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return await response.json();
  }

  // Конвертация файла в base64
  fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result);
      reader.onerror = error => reject(error);
    });
  }

  // Валидация изображений
  validateImages(files) {
    const errors = [];
    
    if (files.length === 0) {
      errors.push('Необходимо загрузить хотя бы одно изображение');
    }
    
    if (files.length > 5) {
      errors.push('Максимум 5 изображений за раз');
    }

    files.forEach((file, index) => {
      if (!file.type.startsWith('image/')) {
        errors.push(`Файл ${index + 1} не является изображением`);
      }
      
      if (file.size > 10 * 1024 * 1024) { // 10MB
        errors.push(`Файл ${index + 1} слишком большой (максимум 10MB)`);
      }
    });

    return errors;
  }
}
```

### 2. React компонент для загрузки товаров

```jsx
import React, { useState, useCallback } from 'react';
import { ProductPhotoAPI } from './api/ProductPhotoAPI';

const ProductPhotoUpload = ({ authToken, onSuccess, onError }) => {
  const [files, setFiles] = useState([]);
  const [formData, setFormData] = useState({
    name: '',
    price: '',
    original_price: '',
    sizes: [],
    colors: [],
    stock_quantity: 0
  });
  const [loading, setLoading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const api = new ProductPhotoAPI(process.env.REACT_APP_API_URL, authToken);

  // Обработка drag & drop
  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    handleFiles(droppedFiles);
  }, []);

  const handleFiles = (newFiles) => {
    const validationErrors = api.validateImages(newFiles);
    if (validationErrors.length > 0) {
      onError(validationErrors.join(', '));
      return;
    }
    
    setFiles(prev => [...prev, ...newFiles].slice(0, 5));
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleArrayInput = (field, value) => {
    const array = value.split(',').map(item => item.trim()).filter(Boolean);
    setFormData(prev => ({ ...prev, [field]: array }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (files.length === 0) {
      onError('Необходимо загрузить хотя бы одно изображение');
      return;
    }

    if (!formData.price || formData.price <= 0) {
      onError('Необходимо указать корректную цену');
      return;
    }

    setLoading(true);
    
    try {
      // Конвертируем файлы в base64
      const images_base64 = await Promise.all(
        files.map(file => api.fileToBase64(file))
      );

      const uploadData = {
        images_base64,
        name: formData.name || undefined, // Отправляем undefined если пустое
        price: parseFloat(formData.price),
        original_price: formData.original_price ? parseFloat(formData.original_price) : undefined,
        sizes: formData.sizes,
        colors: formData.colors,
        stock_quantity: parseInt(formData.stock_quantity) || 0
      };

      const result = await api.uploadProductPhotos(uploadData);
      onSuccess(result);
      
      // Сброс формы
      setFiles([]);
      setFormData({
        name: '',
        price: '',
        original_price: '',
        sizes: [],
        colors: [],
        stock_quantity: 0
      });
      
    } catch (error) {
      onError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="product-photo-upload">
      <div className="form-section">
        <h3>Фотографии товара</h3>
        
        {/* Drag & Drop зона */}
        <div 
          className={`file-drop-zone ${dragActive ? 'active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            type="file"
            multiple
            accept="image/*"
            onChange={(e) => handleFiles(Array.from(e.target.files))}
            style={{ display: 'none' }}
            id="file-input"
          />
          <label htmlFor="file-input" className="file-input-label">
            <div className="drop-zone-content">
              <i className="upload-icon">📸</i>
              <p>Перетащите изображения сюда или нажмите для выбора</p>
              <p className="file-limit">До 5 фотографий, максимум 10MB каждая</p>
            </div>
          </label>
        </div>

        {/* Превью загруженных файлов */}
        {files.length > 0 && (
          <div className="file-preview">
            {files.map((file, index) => (
              <div key={index} className="file-preview-item">
                <img 
                  src={URL.createObjectURL(file)} 
                  alt={`Preview ${index + 1}`}
                  className="preview-image"
                />
                <button 
                  type="button" 
                  onClick={() => removeFile(index)}
                  className="remove-file-btn"
                >
                  ✕
                </button>
                <span className="file-name">{file.name}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="form-section">
        <h3>Информация о товаре</h3>
        
        <div className="form-row">
          <label>
            Название товара (опционально)
            <input
              type="text"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              placeholder="Оставьте пустым для автогенерации AI"
              maxLength="200"
            />
            <small>Если не указано, название будет сгенерировано автоматически</small>
          </label>
        </div>

        <div className="form-row">
          <label>
            Цена (тенге) *
            <input
              type="number"
              value={formData.price}
              onChange={(e) => handleInputChange('price', e.target.value)}
              placeholder="15000"
              min="1"
              required
            />
          </label>
          
          <label>
            Цена до скидки (опционально)
            <input
              type="number"
              value={formData.original_price}
              onChange={(e) => handleInputChange('original_price', e.target.value)}
              placeholder="18000"
              min="1"
            />
            <small>Должна быть больше основной цены</small>
          </label>
        </div>

        <div className="form-row">
          <label>
            Размеры (через запятую)
            <input
              type="text"
              value={formData.sizes.join(', ')}
              onChange={(e) => handleArrayInput('sizes', e.target.value)}
              placeholder="S, M, L, XL"
            />
          </label>
          
          <label>
            Цвета (через запятую)
            <input
              type="text"
              value={formData.colors.join(', ')}
              onChange={(e) => handleArrayInput('colors', e.target.value)}
              placeholder="белый, черный, синий"
            />
          </label>
        </div>

        <div className="form-row">
          <label>
            Количество на складе
            <input
              type="number"
              value={formData.stock_quantity}
              onChange={(e) => handleInputChange('stock_quantity', e.target.value)}
              min="0"
            />
          </label>
        </div>
      </div>

      <div className="form-actions">
        <button 
          type="submit" 
          disabled={loading || files.length === 0}
          className="submit-btn"
        >
          {loading ? (
            <>
              <span className="spinner"></span>
              Обработка...
            </>
          ) : (
            'Добавить товар'
          )}
        </button>
      </div>
    </form>
  );
};

export default ProductPhotoUpload;
```

### 3. CSS стили

```css
.product-photo-upload {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.form-section {
  margin-bottom: 30px;
  padding: 20px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.form-section h3 {
  margin-top: 0;
  color: #333;
  border-bottom: 2px solid #007bff;
  padding-bottom: 10px;
}

.file-drop-zone {
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
}

.file-drop-zone:hover,
.file-drop-zone.active {
  border-color: #007bff;
  background-color: #f8f9fa;
}

.drop-zone-content {
  pointer-events: none;
}

.upload-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 16px;
}

.file-limit {
  color: #666;
  font-size: 14px;
}

.file-preview {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 15px;
  margin-top: 20px;
}

.file-preview-item {
  position: relative;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 10px;
  text-align: center;
}

.preview-image {
  width: 100%;
  height: 120px;
  object-fit: cover;
  border-radius: 4px;
  margin-bottom: 8px;
}

.remove-file-btn {
  position: absolute;
  top: 5px;
  right: 5px;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  cursor: pointer;
  font-size: 12px;
}

.file-name {
  font-size: 12px;
  color: #666;
  word-break: break-all;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.form-row label {
  display: block;
}

.form-row label input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-top: 5px;
}

.form-row small {
  color: #666;
  font-size: 12px;
  margin-top: 5px;
  display: block;
}

.form-actions {
  text-align: center;
  padding-top: 20px;
}

.submit-btn {
  background: #007bff;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.submit-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .file-preview {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  }
}
```

### 4. Использование в родительском компоненте

```jsx
import React, { useState } from 'react';
import ProductPhotoUpload from './components/ProductPhotoUpload';

const AdminDashboard = () => {
  const [notification, setNotification] = useState(null);
  const authToken = localStorage.getItem('authToken'); // или из контекста

  const handleSuccess = (product) => {
    setNotification({
      type: 'success',
      message: `Товар "${product.name}" успешно добавлен! AI определил категорию: ${product.category}`
    });
    
    // Дополнительная логика: обновить список товаров, перенаправить и т.д.
  };

  const handleError = (errorMessage) => {
    setNotification({
      type: 'error',
      message: errorMessage
    });
  };

  return (
    <div className="admin-dashboard">
      <h1>Добавление товара</h1>
      
      {notification && (
        <div className={`notification ${notification.type}`}>
          {notification.message}
          <button onClick={() => setNotification(null)}>✕</button>
        </div>
      )}
      
      <ProductPhotoUpload
        authToken={authToken}
        onSuccess={handleSuccess}
        onError={handleError}
      />
    </div>
  );
};

export default AdminDashboard;
```

## Обработка ошибок

### Типичные ошибки API

```javascript
const ERROR_CODES = {
  400: 'Неверные данные запроса',
  401: 'Необходима авторизация',
  403: 'Недостаточно прав доступа',
  404: 'Магазин не найден',
  413: 'Файл слишком большой',
  422: 'Ошибка валидации данных',
  500: 'Внутренняя ошибка сервера'
};

// Обработчик ошибок
const handleAPIError = async (response) => {
  if (!response.ok) {
    let errorMessage;
    
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || ERROR_CODES[response.status] || 'Неизвестная ошибка';
    } catch {
      errorMessage = ERROR_CODES[response.status] || `HTTP ${response.status}`;
    }
    
    throw new Error(errorMessage);
  }
  
  return response.json();
};
```

## Валидация на фронтенде

```javascript
const validateProductData = (formData, files) => {
  const errors = [];
  
  // Проверка изображений
  if (files.length === 0) {
    errors.push('Необходимо загрузить хотя бы одно изображение');
  }
  
  // Проверка цены
  if (!formData.price || formData.price <= 0) {
    errors.push('Цена должна быть больше 0');
  }
  
  // Проверка скидочной цены
  if (formData.original_price && formData.original_price <= formData.price) {
    errors.push('Цена до скидки должна быть больше текущей цены');
  }
  
  // Проверка названия
  if (formData.name && formData.name.length > 200) {
    errors.push('Название не должно превышать 200 символов');
  }
  
  return errors;
};
```

## UI/UX Рекомендации

### 1. Прогресс загрузки
- Показывать спиннер во время обработки
- Индикатор прогресса для загрузки файлов
- Блокировать кнопку отправки во время обработки

### 2. Превью результата
```jsx
const ProductPreview = ({ product }) => (
  <div className="product-preview">
    <h4>AI анализ завершен:</h4>
    <div className="ai-results">
      <p><strong>Категория:</strong> {product.category}</p>
      <p><strong>Характеристики:</strong> {product.features.join(', ')}</p>
      <p><strong>Бренд:</strong> {product.brand}</p>
    </div>
    <div className="product-images">
      {product.image_urls.map((url, index) => (
        <img key={index} src={url} alt={`Product ${index + 1}`} />
      ))}
    </div>
  </div>
);
```

### 3. Уведомления
- Успешное создание товара
- Информация о AI анализе
- Предупреждения о больших файлах
- Подтверждения действий

## Тестирование

### Тестовые сценарии

```javascript
// Тест с валидными данными
const testValidUpload = async () => {
  const testData = {
    images_base64: ['data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='],
    name: 'Тестовая рубашка',
    price: 15000,
    original_price: 18000,
    sizes: ['S', 'M', 'L'],
    colors: ['белый'],
    stock_quantity: 10
  };
  
  const result = await api.uploadProductPhotos(testData);
  console.log('✅ Товар создан:', result);
};

// Тест без названия (AI генерация)
const testAIGeneration = async () => {
  const testData = {
    images_base64: ['data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='],
    // name не указан - должен быть сгенерирован AI
    price: 12000,
    sizes: ['M'],
    colors: ['синий'],
    stock_quantity: 5
  };
  
  const result = await api.uploadProductPhotos(testData);
  console.log('✅ AI название:', result.name);
};
```

## Заключение

Этот API позволяет админам магазинов легко добавлять товары через фотографии с минимальными усилиями. AI автоматически анализирует характеристики одежды, что значительно ускоряет процесс каталогизации товаров.

**Ключевые преимущества:**
- 🤖 **AI анализ** автоматически определяет характеристики
- 📸 **Множественные фото** в одном запросе
- 🎯 **Гибкость названий** (ручные или AI)
- 💰 **Поддержка скидок** 
- ⚡ **Быстрая обработка** благодаря параллельной загрузке
- 🛡️ **Полная валидация** на всех уровнях 