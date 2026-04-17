# REST API Error Guide

## Формат ответа
Любая стандартизированная ошибка (от `400 Bad Request` до `504 Gateway Timeout`), которую отдает бекенд Mini App, имеет фиксированный JSON-формат. 
Это гарантирует, что фронтенд всегда знает, как разобрать и отобразить описание проблемы.

```json
{
  "error": {
    "code": "STRING_ERROR_CODE",
    "message": "Human readable message containing details"
  }
}
```

## Доступные коды (`code`)
| Код ответа `status` | Константа `code` | Описание сценария | Фронтенд-Действие |
|-------------------|------------------|-------------------|-------------------|
| `400` | `BAD_REQUEST` | Невалидный JSON, отсутствуют обязательные поля (`init_data` и т.д). | Подсветить ошибку разработки. |
| `401` | `UNAUTHORIZED` | Неверная подпись `initData` от Telegram, устаревший или испорченный JWT токен. | Попросить переоткрыть Web App. |
| `500` | `INTERNAL_SERVER_ERROR` | Непредсказуемая поломка сервиса. | Статический экран "Все сломалось". |
| `503` | `SERVICE_UNAVAILABLE` | База данных "лежит" или перегружена (отбой от SQLAlchemy). | Экран "Мы чиним, зайдите позже". |
| `504` | `GATEWAY_TIMEOUT` | База данных или другой сервис не ответили в заданное время. | Экран "Долгое ожидание, попробуйте снова". |

## Пример реализации обработки на клиенте:
```javascript
const response = await fetch('/auth/telegram', { ... });
if (!response.ok) {
    const data = await response.json();
    const errorCode = data.error.code; // 'UNAUTHORIZED'
    const errorMsg = data.error.message; // 'Token has expired'
    // Вызов стейта ошибки
}
```
