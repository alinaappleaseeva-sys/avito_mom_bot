import json
from typing import List, Dict, Any

# ==========================================
# ПРОТОТИПЫ ИНСТРУМЕНТОВ АГЕНТА (Спринт 1)
# ==========================================

def search_tariffs(provider: str) -> List[Dict[str, Any]]:
    """
    (MOCK) Собирает тарифы и модели оплаты для провайдера.
    На реальном проекте здесь будет код парсинга HTML или HTTP-запросы к API.
    LLM опционально может использоваться как "очиститель" мутного HTML, 
    но тут мы отдаем четкие структуры.
    """
    print(f"[TOOL] Поиск тарифов для {provider}...")
    
    # Мок-данные. LLM здесь не применяется. Это чистый ответ от внешнего мира.
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
                "approx_cost_for_3_months": 1500,  # ~500 руб/мес
                "billing_notes": "почасовой биллинг, списание с баланса, без обязательств",
            },
            {
                "provider": "Selectel",
                "name": "Storage Node",
                "vCPU": 1,
                "ram_gb": 1,
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
                "approx_cost_for_3_months": 2100, # (700 руб/мес)
                "billing_notes": "Строго предоплата за весь год.",
            }
        ]
    return []

def analyze_billing(offers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Отсев тарифов по конфигурации и биллингу.
    
    ЗДЕСЬ КОД: Производится жесткая математическая фильтрация (ОЗУ >= 2, диск >= 30, нет слову 'yearly').
    ЗДЕСЬ МОЖЕТ БЫТЬ LLM: Если `billing_notes` содержит сложный неформатированный текст с сайта, 
    мы вызываем LLM_Client("вытащи из этого текста модель оплаты").
    """
    print(f"[TOOL] Анализ {len(offers)} офферов...")
    candidates = []
    
    for offer in offers:
        # 1. Жесткие фильтры в коде
        if offer.get("vCPU", 0) < 1: continue
        if offer.get("ram_gb", 0) < 2: continue
        if offer.get("disk_gb", 0) < 30: continue
        
        # 2. Бюджетный фильтр (до 2000 руб за 3 месяца)
        if offer.get("approx_cost_for_3_months", 9999) > 2000:
            continue
            
        # 3. Фильтр моделей оплаты
        model = offer.get("billing_model", "")
        # Исключаем годовые депозиты кодом
        if model == "yearly_deposit" or offer.get("min_period_months", 1) >= 12:
            continue
            
        candidates.append(offer)
        
    return candidates

def compare_candidates(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Простой скоринг и выбор лучшего кандидата.
    
    ЗДЕСЬ КОД: Сортирует кандидатов по штрафам/баллам (pay-as-you-go - лучше, дешевле - лучше).
    ЗДЕСЬ LLM: После того как код выбрал топ-1, LLM формирует поле "explainable_reason", 
    объясняя пользователю человеческим языком, почему это хороший выбор.
    """
    print(f"[TOOL] Сравнение {len(candidates)} кандидатов...")
    if not candidates:
        return {}

    # Задаем базовый скоринг в коде
    def score_offer(offer):
        score = 100
        # Штрафуем за высокую цену
        score -= offer.get("approx_cost_for_3_months", 0) * 0.01 
        
        # Бонус за pay_as_you_go
        if offer.get("billing_model") == "pay_as_you_go":
            score += 20
        # Бонус за приоритет (Selectel > RUVDS)
        if offer.get("provider") == "Selectel":
            score += 10
            
        return score

    # Сортируем
    sorted_candidates = sorted(candidates, key=score_offer, reverse=True)
    best = sorted_candidates[0]
    
    # Имитация вызова LLM для объяснения (в реальном коде тут будет запрос к gpt/claude)
    best["why"] = (
        "[Сгенерировано LLM] Мы выбрали этот тариф, так как он "
        f"не требует годового залога (модель: {best.get('billing_model')}) "
        f"при оптимальной цене в {best.get('approx_cost_for_3_months')} руб. за 3 месяца."
    )
    return best

def generate_checkout_flow(provider: str, tariff: Dict[str, Any]) -> str:
    """
    Текстовое/JSON описание шагов покупки. 
    ВАЖНО: Нет реальной автоматизации (клик / ввод).
    
    ЗДЕСЬ LLM: LLM принимает на вход `provider` и `tariff` и используя свои знания / контекст
    генерирует Markdown с пошаговой инструкцией.
    """
    print(f"[TOOL] Генерация checkout_flow для {provider}...")
    
    # Имитация ответа от LLM (в реальном коде тут промпт к LLM)
    markdown_instruction = f"""
## Инструкция по покупке: {provider} - {tariff.get('name')}

1. **Регистрация**: Зайди на официальный сайт {provider} и зарегистрируйся.
2. **Баланс**: Перейди в раздел "Баланс". Тебе потребуется внести около {tariff.get('approx_cost_for_3_months')} рублей для работы сервера на 3 месяца.
3. **Создание сервера**:
   - Выбери регион **{tariff.get('region')}**.
   - Выбери ОС **Ubuntu 24.04**.
   - Конфигурация: {tariff.get('vCPU')} vCPU / {tariff.get('ram_gb')} GB RAM / {tariff.get('disk_gb')} GB Disk.

> [!WARNING] Обязательный чек безопасности:
> Сверься с реальным экраном перед оплатой. Есть ли там слова "депозит", "год", "предоплата"? Если есть — остановись! Инструкции на страницах провайдера могут расходиться с нашим анализом.
"""
    return markdown_instruction

def validate_result(vps_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Проверяет, что фактический результат соответствует ожиданиям.
    
    ЗДЕСЬ КОД: Сравниваем IP (что он есть), проверяем числа (RAM, CPU).
    ЗДЕСЬ LLM: Читает `billing_page_text` (скриншот/текст от юзера), выискивая скрытые депозиты.
    """
    print("[TOOL] Валидация созданного VPS...")
    
    # Имитация логики
    issues = []
    
    # Это бы делал LLM: анализ текста
    if "оплата за год" in str(vps_info.get("billing_page_text", "")).lower():
        issues.append("Найден текст 'оплата за год' на странице биллинга!")
        
    # Это легко делает код: жесткие фильтры
    if vps_info.get("ram_gb", 2) < 2:
        issues.append("Созданный сервер имеет меньше RAM, чем заявлено (минимум 2).")

    is_ok = len(issues) == 0
    
    report = {
        "ok": is_ok,
        "issues": issues,
        "recommendations": []
    }
    
    if not is_ok:
        report["recommendations"].append("Отмени тариф или смени способ оплаты, если не готов к депозиту.")
    else:
        report["recommendations"].append("Отлично! Теперь можно деплоить avito_mom_bot.")
        
    return report
