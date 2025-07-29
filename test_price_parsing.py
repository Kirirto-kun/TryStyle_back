#!/usr/bin/env python3
"""
Тестовый скрипт для проверки парсинга цен из HTML
"""

import re
from qazaq_republic_scraper import QazaqRepublicScraper

def test_price_parsing():
    """
    Тестирует парсинг различных форматов цен
    """
    scraper = QazaqRepublicScraper()
    
    # Тестовые случаи
    test_cases = [
        # Обычная цена
        '<div class="catalog_item__price">11000₸</div>',
        
        # Цена со скидкой
        '<div class="catalog_item__price">11000₸<span>22000₸</span></div>',
        
        # Цена с пробелами
        '<div class="catalog_item__price">11 000₸</div>',
        
        # Скидка с пробелами
        '<div class="catalog_item__price">11 000₸<span>22 000₸</span></div>',
        
        # Сложный случай
        '<div class="catalog_item__price">7 700₸<span>11 000₸</span></div>',
        
        # Проблемный случай из примера
        '<div class="catalog_item__price">12800₸<span>16000₸</span></div>',
        
        # Еще один случай
        '<div class="catalog_item__price">24000₸</div>',
    ]
    
    print("Тестирование парсинга цен:")
    print("=" * 50)
    
    for i, test_html in enumerate(test_cases, 1):
        print(f"\nТест {i}: {test_html}")
        
        try:
            price, original_price = scraper._parse_price_from_html(test_html)
            
            if original_price:
                print(f"  ✅ Результат: {price}₸ (скидка с {original_price}₸)")
            else:
                print(f"  ✅ Результат: {price}₸ (без скидки)")
                
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")

if __name__ == "__main__":
    test_price_parsing()