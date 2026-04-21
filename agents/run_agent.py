import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.vps_agent.tools import (
    search_tariffs,
    analyze_billing,
    compare_candidates,
    generate_checkout_flow,
    validate_result
)
from agents.vps_agent.config import PROVIDERS_PRIORITY

def main():
    print("=== VPS Agent Pipeline (Спринт 1: Mocked Linear Flow) ===\n")
    
    requirements = {
        "min_vcpu": 1,
        "min_ram_gb": 2,
        "min_disk_gb": 30,
        "region_pref": "ru-msk",
        "max_budget_for_3_months": 2000
    }
    
    print(f"[Шаг 0] Требования: {requirements}\n")

    all_offers = []
    
    # Шаг 1
    print("[Шаг 1] Сбор данных...")
    for provider in PROVIDERS_PRIORITY:
        offers = search_tariffs(provider)
        all_offers.extend(offers)
        
    print(f"Всего собрано сырых офферов: {len(all_offers)}\n")
    
    # Шаг 2
    print("[Шаг 2] Фильтрация тарифов (код)...")
    candidates = analyze_billing(all_offers, requirements)
    
    print(f"Тарифов прошло жесткий фильтр: {len(candidates)}")
    for c in candidates:
        print(f"  - {c['provider']} | {c['name']} | {c['approx_cost_for_3_months']} руб/3мес")
    print()
    
    if not candidates:
        print("❌ Подходящих тарифов не найдено. Попробуйте смягчить ограничения.")
        return

    # Шаг 3
    print("[Шаг 3] Выбор лучшего тарифа (скоринг + LLM)...")
    best_offer = compare_candidates(candidates)
    print(f"🏆 Победитель: {best_offer['provider']} - {best_offer['name']}")
    print(f"📝 Пояснение агента: {best_offer.get('why', 'Нет пояснения')}\n")
    
    # Шаг 4
    print("[Шаг 4] Генерация Markdown инструкции (LLM)...")
    checkout_markdown = generate_checkout_flow(best_offer['provider'], best_offer)
    print("="*60)
    print(checkout_markdown)
    print("="*60)

    # Шаг 5
    print("\n[Шаг 5] Имитация валидации результата...")
    mock_post_checkout = {
        "ip": "10.0.0.1",
        "ram_gb": 2,
        "region": "ru-msk",
        "billing_page_text": "Оплата успешно прошла. Дата следующего списания: через месяц."
    }
    report = validate_result(mock_post_checkout, requirements)
    
    if report["ok"]:
        print("✅ Валидация пройдена:", report["recommendations"][0])
    else:
        print("❌ Ошибки при валидации:")
        for issue in report["issues"]:
            print(f"  - {issue}")

if __name__ == "__main__":
    main()
