#!/usr/bin/env python
"""
Быстрый скрипт для просмотра features товаров
"""
import sys
import os
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

def main():
    """Быстрый просмотр features."""
    try:
        print("🔍 БЫСТРЫЙ АНАЛИЗ FEATURES")
        print("=" * 60)
        
        db = get_db_session()
        products = db.query(Product).join(Store).order_by(Product.id).all()
        
        if not products:
            print("❌ Каталог пуст!")
            return
        
        print(f"📦 Анализируем {len(products)} товаров:\n")
        
        for i, product in enumerate(products, 1):
            print(f"{i}. 📝 {product.name}")
            print(f"   💰 ₸{product.price:,.0f} | 📂 {product.category}")
            
            if product.features:
                features_str = "', '".join(product.features)
                print(f"   🏷️  Features: ['{features_str}']")
            else:
                print("   ❌ Нет features")
            print()
        
        # Быстрая статистика
        all_features = []
        for product in products:
            if product.features:
                all_features.extend(product.features)
        
        if all_features:
            from collections import Counter
            feature_counts = Counter(all_features)
            print("🏆 ТОП FEATURES:")
            for feature, count in feature_counts.most_common(5):
                print(f"   {count}x '{feature}'")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main() 