#!/usr/bin/env python
"""
Полная проверка всех товаров в каталоге и анализ их features.
Показывает результаты улучшений системы генерации features.
"""
import sys
import os
from collections import defaultdict, Counter
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database import get_db_session
from src.models.product import Product
from src.models.store import Store
# Импортируем все модели для избежания проблем с зависимостями SQLAlchemy
from src.models.review import Review
from src.models.user import User
from src.models.clothing import ClothingItem
from src.models.chat import Chat, Message
from src.models.tryon import TryOn
from src.models.waitlist import WaitListItem

def analyze_features_quality(features):
    """Анализирует качество features товара."""
    if not features:
        return {
            'score': 0,
            'quality': 'НЕТ FEATURES',
            'details': 'Отсутствуют features'
        }
    
    feature_count = len(features)
    
    # Категории для анализа
    color_keywords = ['черный', 'белый', 'синий', 'красный', 'зеленый', 'серый', 'коричневый', 'розовый', 'желтый', 'navy', 'black', 'white', 'blue', 'red', 'gray', 'pink']
    style_keywords = ['классический', 'спортивный', 'casual', 'деловой', 'vintage', 'modern', 'contemporary', 'relaxed', 'fitted', 'oversized']
    material_keywords = ['хлопок', 'cotton', 'denim', 'wool', 'polyester', 'silk', 'leather', 'jersey', 'fleece']
    construction_keywords = ['молния', 'пуговицы', 'карманы', 'капюшон', 'воротник', 'манжеты', 'zip', 'button', 'pocket', 'hood', 'collar']
    
    categories_found = {
        'colors': sum(1 for f in features if any(color in f.lower() for color in color_keywords)),
        'styles': sum(1 for f in features if any(style in f.lower() for style in style_keywords)), 
        'materials': sum(1 for f in features if any(material in f.lower() for material in material_keywords)),
        'construction': sum(1 for f in features if any(construction in f.lower() for construction in construction_keywords))
    }
    
    total_categories = sum(1 for count in categories_found.values() if count > 0)
    
    # Оценка качества
    if feature_count >= 15 and total_categories >= 3:
        quality = 'ОТЛИЧНЫЕ'
        score = 5
    elif feature_count >= 10 and total_categories >= 2:
        quality = 'ХОРОШИЕ'
        score = 4
    elif feature_count >= 7 and total_categories >= 2:
        quality = 'СРЕДНИЕ'
        score = 3
    elif feature_count >= 5:
        quality = 'БАЗОВЫЕ'
        score = 2
    else:
        quality = 'ПЛОХИЕ'
        score = 1
    
    details = f"{feature_count} features, {total_categories} категорий"
    return {
        'score': score,
        'quality': quality,
        'details': details,
        'categories': categories_found,
        'count': feature_count
    }

def main():
    """Главная функция анализа каталога."""
    try:
        print("🔍 ПОЛНЫЙ АНАЛИЗ ТОВАРОВ И FEATURES В КАТАЛОГЕ")
        print("=" * 80)
        
        db = get_db_session()
        products = db.query(Product).join(Store).order_by(Product.id).all()
        
        if not products:
            print("❌ Каталог пуст!")
            return
        
        print(f"📦 Анализируем {len(products)} товаров в каталоге H&M Казахстан\n")
        
        # Инициализация статистики
        stats = {
            'total': len(products),
            'excellent': 0,  # 15+ features, 3+ категории
            'good': 0,       # 10+ features, 2+ категории
            'average': 0,    # 7+ features, 2+ категории
            'basic': 0,      # 5+ features
            'poor': 0,       # <5 features
            'no_features': 0
        }
        
        category_stats = defaultdict(list)
        all_features = []
        examples = {
            'excellent': [],
            'poor': [],
            'no_features': []
        }
        
        # Анализ каждого товара
        for i, product in enumerate(products, 1):
            analysis = analyze_features_quality(product.features)
            
            print(f"{i:3d}. 📝 {product.name}")
            print(f"     💰 ₸{product.price:,.0f} | 📂 {product.category} | 🏪 {product.store.name}")
            
            if product.features:
                features_display = "', '".join(product.features[:5])  # Показываем первые 5
                more_text = f" + еще {len(product.features) - 5}" if len(product.features) > 5 else ""
                print(f"     🏷️  [{analysis['count']}] Features: ['{features_display}']{more_text}")
                print(f"     ⭐ Качество: {analysis['quality']} ({analysis['details']})")
            else:
                print("     ❌ НЕТ FEATURES")
            
            # Статистика по качеству
            if analysis['score'] == 5:
                stats['excellent'] += 1
                if len(examples['excellent']) < 3:
                    examples['excellent'].append(product)
            elif analysis['score'] == 4:
                stats['good'] += 1
            elif analysis['score'] == 3:
                stats['average'] += 1
            elif analysis['score'] == 2:
                stats['basic'] += 1
            elif analysis['score'] == 1:
                stats['poor'] += 1
                if len(examples['poor']) < 3:
                    examples['poor'].append(product)
            else:
                stats['no_features'] += 1
                if len(examples['no_features']) < 3:
                    examples['no_features'].append(product)
            
            # Статистика по категориям
            category_stats[product.category].append(analysis)
            
            if product.features:
                all_features.extend(product.features)
            
            print()
        
        # ОБЩАЯ СТАТИСТИКА
        print("\n" + "="*80)
        print("📊 СТАТИСТИКА КАЧЕСТВА FEATURES")
        print("="*80)
        
        print(f"📦 Всего товаров: {stats['total']}")
        print(f"🌟 Отличные features (15+ характеристик): {stats['excellent']} ({stats['excellent']/stats['total']*100:.1f}%)")
        print(f"✅ Хорошие features (10+ характеристик): {stats['good']} ({stats['good']/stats['total']*100:.1f}%)")
        print(f"🔶 Средние features (7+ характеристик): {stats['average']} ({stats['average']/stats['total']*100:.1f}%)")
        print(f"🔸 Базовые features (5+ характеристик): {stats['basic']} ({stats['basic']/stats['total']*100:.1f}%)")
        print(f"⚠️  Плохие features (<5 характеристик): {stats['poor']} ({stats['poor']/stats['total']*100:.1f}%)")
        print(f"❌ Без features: {stats['no_features']} ({stats['no_features']/stats['total']*100:.1f}%)")
        
        # Качественные товары (хорошие + отличные)
        quality_products = stats['excellent'] + stats['good']
        print(f"\n🎯 Товары с качественными features: {quality_products} ({quality_products/stats['total']*100:.1f}%)")
        
        # СТАТИСТИКА ПО КАТЕГОРИЯМ
        print(f"\n📂 АНАЛИЗ ПО КАТЕГОРИЯМ ТОВАРОВ")
        print("-"*60)
        
        for category, analyses in category_stats.items():
            if not analyses:
                continue
                
            avg_features = sum(a['count'] for a in analyses) / len(analyses)
            excellent_in_cat = sum(1 for a in analyses if a['score'] == 5)
            
            print(f"{category.upper():15s} | {len(analyses):3d} товаров | {avg_features:5.1f} features в среднем | {excellent_in_cat} отличных")
        
        # ПРИМЕРЫ ЛУЧШИХ FEATURES
        print(f"\n🌟 ПРИМЕРЫ ОТЛИЧНЫХ FEATURES (15+ характеристик)")
        print("-"*80)
        
        for product in examples['excellent']:
            print(f"✨ {product.name}")
            print(f"   Features [{len(product.features)}]: {', '.join(product.features)}")
            print()
        
        # ПРИМЕРЫ ПЛОХИХ FEATURES
        if examples['poor']:
            print(f"⚠️  ПРИМЕРЫ ТОВАРОВ С ПЛОХИМИ FEATURES")
            print("-"*80)
            
            for product in examples['poor']:
                features_text = ', '.join(product.features) if product.features else "НЕТ"
                print(f"❌ {product.name}")
                print(f"   Features [{len(product.features) if product.features else 0}]: {features_text}")
                print()
        
        # ТОП FEATURES
        if all_features:
            print(f"🏷️  ТОП-20 ПОПУЛЯРНЫХ FEATURES")
            print("-"*60)
            
            feature_counts = Counter(all_features)
            for feature, count in feature_counts.most_common(20):
                print(f"{feature:35s} | {count:3d} товаров")
        
        # РЕКОМЕНДАЦИИ
        print(f"\n💡 РЕКОМЕНДАЦИИ")
        print("-"*40)
        
        if stats['no_features'] > 0:
            print(f"🔴 {stats['no_features']} товаров без features - требуется анализ изображений")
        
        if stats['poor'] > 0:
            print(f"🟠 {stats['poor']} товаров с плохими features - можно улучшить")
        
        improvement_percent = (quality_products / stats['total']) * 100
        if improvement_percent >= 70:
            print(f"🎉 ОТЛИЧНО! {improvement_percent:.1f}% товаров имеют качественные features")
        elif improvement_percent >= 50:
            print(f"✅ ХОРОШО! {improvement_percent:.1f}% товаров имеют качественные features")
        else:
            print(f"⚠️  НУЖНО УЛУЧШИТЬ: только {improvement_percent:.1f}% товаров имеют качественные features")
        
        print(f"\n🔍 Анализ завершен успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка при анализе каталога: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            try:
                db.close()
                print("✅ Соединение с БД закрыто")
            except Exception as close_error:
                print(f"⚠️  Ошибка закрытия БД: {close_error}")

if __name__ == "__main__":
    main() 