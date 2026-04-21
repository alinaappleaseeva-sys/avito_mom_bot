import re
from typing import List, Dict, Any, Optional

from agents.vps_agent.config import SCORING_WEIGHTS, PROVIDERS_PRIORITY

def search_tariffs(provider: str) -> List[Dict[str, Any]]:
    """
    (MOCK) Собирает тарифы и модели оплаты для провайдера.
    """
    print(f"[TOOL] Поиск тарифов для {provider}...")
    
    if provider.lower() == "selectel":
        return [
            {
                "provider": "Selectel",
                "name": "Cloud Server S-1",
                "vCPU": 1,
                "ram_gb": 2,
                "disk_gb": 30,
                "region": "ru-msk-1",
                "os_images": ["Ubuntu 22.04", "Ubuntu 24.04"],
                "billing_model": "pay_as_you_go",
                "min_period_months": 0,
                "approx_cost_for_3_months": 1500,  
                "billing_notes": "почасовой биллинг, списание с баланса, без обязательств",
            },
            {
                "provider": "Selectel",
                "name": "Storage Node",
                "vCPU": 1,
                "ram_gb": 1, # Слишком мало RAM, должно отсеяться
                "disk_gb": 250,
                "region": "ru-msk-1",
                "os_images": ["Ubuntu 22.04"],
                "billing_model": "pay_as_you_go",
                "min_period_months": 0,
                "approx_cost_for_3_months": 2200, 
                "billing_notes": "почасовой биллинг",
            }
        ]
    elif provider.lower() == "ruvds":
        return [
            {
                "provider": "RUVDS",
                "name": "Start+",
                "vCPU": 1,
                "ram_gb": 2,
                "disk_gb": 30,
                "region": "ru-msk-1",
                "os_images": ["Ubuntu 24.04"],
                "billing_model": "monthly",
                "min_period_months": 1,
                "approx_cost_for_3_months": 900,  
                "billing_notes": "Оплата помесячно. Депозитов нет.",
            },
            {
                "provider": "RUVDS",
                "name": "Promo-Yearly",
                "vCPU": 2,
                "ram_gb": 4,
                "disk_gb": 60,
                "region": "ru-msk-1",
                "os_images": ["Ubuntu 22.04"],
                "billing_model": "yearly_deposit",
                "min_period_months": 12,
                "approx_cost_for_3_months": 2100, 
                "billing_notes": "Строго предоплата за весь год.",
            }
        ]
    return []

def analyze_billing(offers: List[Dict[str, Any]], requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Отсев тарифов по конфигурации `requirements` и биллингу.
    """
    print(f"[TOOL] Анализ {len(offers)} офферов (бюджет <= {requirements.get('max_budget_for_3_months')} руб)...")
    candidates = []
    
    # В реальности тут может быть LLM для сложного текста
    dangerous_keywords = ["предоплата за год", "оплата за 12", "депозит за год", "годовая подписка"]
    
    for offer in offers:
        # 1. Жесткие фильтры железа из requirements
        if offer.get("vCPU", 0) < requirements.get("min_vcpu", 1): continue
        if offer.get("ram_gb", 0) < requirements.get("min_ram_gb", 2): continue
        if offer.get("disk_gb", 0) < requirements.get("min_disk_gb", 30): continue
        
        # 2. Бюджетный фильтр
        max_budget = requirements.get("max_budget_for_3_months", float('inf'))
        if offer.get("approx_cost_for_3_months", 99999) > max_budget:
            continue
            
        # 3. Фильтр моделей оплаты (структурированный)
        model = offer.get("billing_model", "")
        if model == "yearly_deposit" or offer.get("min_period_months", 1) >= 12:
            continue
            
        # 4. Анализ `billing_notes` (защита от "мелкого шрифта")
        notes = str(offer.get("billing_notes", "")).lower()
        if any(kw in notes for kw in dangerous_keywords):
            continue  # Отбраковываем, если в тексте промелькнул залог
            
        candidates.append(offer)
        
    return candidates

def compare_candidates(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Скорринг на основе `SCORING_WEIGHTS` и выбор лучшего.
    """
    print(f"[TOOL] Сравнение {len(candidates)} кандидатов...")
    if not candidates:
        return {}

    def score_offer(offer):
        score = SCORING_WEIGHTS["base_score"]
        # Штраф за высокую цену
        price = offer.get("approx_cost_for_3_months", 0)
        score -= price * SCORING_WEIGHTS["price_penalty_multiplier"]
        
        # Бонус за pay_as_you_go
        if offer.get("billing_model") == "pay_as_you_go":
            score += SCORING_WEIGHTS["pay_as_you_go_bonus"]
            
        # Бонус за приоритетного провайдера (если он первый в списке)
        top_provider = PROVIDERS_PRIORITY[0] if PROVIDERS_PRIORITY else None
        if top_provider and offer.get("provider") == top_provider:
            score += SCORING_WEIGHTS["priority_provider_bonus"]
            
        return score

    sorted_candidates = sorted(candidates, key=score_offer, reverse=True)
    best = sorted_candidates[0]
    
    # Объяснение выбора (имитация LLM)
    best["why"] = (
        "[Сгенерировано LLM] Мы выбрали этот тариф, так как он "
        f"работает по модели '{best.get('billing_model')}' "
        f"при оптимальной цене в {best.get('approx_cost_for_3_months')} руб. за 3 месяца."
    )
    return best

def generate_checkout_flow(provider: str, tariff: Dict[str, Any]) -> str:
    """Генерация пошаговой инструкции (Markdown)"""
    print(f"[TOOL] Генерация checkout_flow для {provider}...")
    
    return f"""
## Инструкция по покупке: {provider} - {tariff.get('name')}

1. **Баланс**: Пополни счет примерно на {tariff.get('approx_cost_for_3_months')} руб. (для ~3 месяцев работы).
2. **Создание сервера**:
   - Выбери регион **{tariff.get('region')}**.
   - Выбери ОС **Ubuntu 24.04**.
   - Конфигурация: {tariff.get('vCPU')} vCPU / {tariff.get('ram_gb')} GB RAM / {tariff.get('disk_gb')} GB Disk.

> [!WARNING] Обязательный чек безопасности
> Сверься с экраном перед нажатием "создать/оплатить". Если где-то появилась плашка "годовой депозит", "подписка на 12 мес", немедленно останови процесс.
"""

def validate_result(vps_info: Dict[str, Any], requirements: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Расширенная валидация сервера после покупки.
    """
    print("[TOOL] Валидация созданного VPS...")
    issues = []
    
    if requirements:
        if vps_info.get("ram_gb", 0) < requirements.get("min_ram_gb", 2):
            issues.append(f"RAM ({vps_info.get('ram_gb')}) меньше требуемого ({requirements.get('min_ram_gb')}).")
        
        region = vps_info.get("region", "").lower()
        if "ru" not in region and "msk" not in region:
             issues.append(f"Регион сервера '{region}' не похож на требуемый (RU/MSK).")
             
    if not vps_info.get("ip"):
        issues.append("Не найден IP-адрес сервера. Сервер еще не создан?")

    # Имитация работы LLM по парсингу текста (работа кодом с паттернами)
    page_text = str(vps_info.get("billing_page_text", "")).lower()
    dangerous_patterns = [r"оплата за 1?2 (мес|год)", r"депозит\b", r"\bгод\b.*предоплата"]
    for pat in dangerous_patterns:
        if re.search(pat, page_text):
            issues.append("Найден потенциальный годовой депозит или скрытая подписка на странице оплаты!")
            break

    is_ok = len(issues) == 0
    
    return {
        "ok": is_ok,
        "issues": issues,
        "recommendations": [] if not is_ok else ["Отлично! Можно переходить к клонированию репозитория."]
    }
