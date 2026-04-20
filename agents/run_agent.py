import sys
import os

# Добавляем корневую папку проекта в sys.path, чтобы импорты работали при запуске из любой директории
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.vps_agent_tools import (
    search_tariffs,
    analyze_billing,
    compare_candidates,
    generate_checkout_flow,
    validate_result
)

PROVIDERS_PRIORITY = ["Selectel", "RUVDS"]

def main():
    print("=== VPS Agent Pipeline (Спринт 1: Mocked Linear Flow) ===\n")
    
    # Шаг 0: Сбор требований (Здесь имитация)
    print("[Шаг 0] Пользователь запросил сервер: 1 vCPU, =>2 RAM, =>30 GB. Бюджет: до 2000р/3мес. Строго без годовых депозитов.\n")

    all_offers = []
    
    # Шаг 1: Сбор данных
    print("[Шаг 1] Сбор данных по провайдерам...")
    for provider in PROVIDERS_PRIORITY:
        offers = search_tariffs(provider)
        all_offers.extend(offers)
        
    print(f"Всего собрано сырых офферов: {len(all_offers)}\n")
    
    # Шаг 2: Анализ биллинга
    print("[Шаг 2] Фильтрация тарифов (код)...")
    candidates = analyze_billing(all_offers)
    
    print(f"Тарифов прошло жесткий фильтр: {len(candidates)}")
    for c in candidates:
        print(f"  - {c['provider']} | {c['name']} | {c['approx_cost_for_3_months']} руб/3мес")
    print()
    
    if not candidates:
        print("❌ Подходящих тарифов не найдено. Попробуйте смягчить ограничения.")
        return

    # Шаг 3: Сравнение и выбор лучшего
    print("[Шаг 3] Выбор лучшего тарифа (скоринг + LLM)...")
    best_offer = compare_candidates(candidates)
    print(f"🏆 Победитель: {best_offer['provider']} - {best_offer['name']}")
    print(f"📝 Пояснение агента: {best_offer.get('why', 'Нет пояснения')}\n")
    
    # Шаг 4: Генерация инструкций
    print("[Шаг 4] Генерация Markdown инструкции (LLM)...")
    checkout_markdown = generate_checkout_flow(best_offer['provider'], best_offer)
    print("="*60)
    print(checkout_markdown)
    print("="*60)

    # Шаг 5: Имитация проверки (пользователь вернулся с данными после покупки)
    print("\n[Шаг 5] Имитация валидации результата (post-checkout)...")
    mock_user_validation_data = {
        "ram_gb": 2,
        "billing_page_text": "К оплате 500 руб. Дата следующего списания: через месяц. Депозитов нет."
    }
    report = validate_result(mock_user_validation_data)
    if report["ok"]:
        print("✅ Валидация пройдена:", report["recommendations"][0])
    else:
        print("❌ Ошибки при валидации:")
        for issue in report["issues"]:
            print(f"  - {issue}")


if __name__ == "__main__":
    main()
