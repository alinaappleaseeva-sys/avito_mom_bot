from typing import Dict, List, Any

# Приоритет проверки провайдеров
PROVIDERS_PRIORITY: List[str] = ["Selectel", "RUVDS", "FirstVDS", "Timeweb"]

# Правила скоринга (веса)
SCORING_WEIGHTS = {
    "base_score": 100,
    "price_penalty_multiplier": 0.01,  # За каждый рубль цены вычитаем 0.01 балла (т.е. 1 балл за каждые 100 руб)
    "pay_as_you_go_bonus": 20,         # Бонус за почасовой биллинг
    "priority_provider_bonus": 10      # Бонус, если провайдер первый в списке приоритетов (например, Selectel)
}
