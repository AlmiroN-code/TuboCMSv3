# Система приоритетов обработки видео

## Описание

Система приоритетной очереди обеспечивает быструю обработку для premium пользователей и важного контента.

## Уровни приоритетов

| Приоритет | Пользователи | Описание |
|-----------|--------------|----------|
| 9-10 | Premium | Критический приоритет |
| 7-8 | Premium | Высокий приоритет |
| 5 | Обычные | Стандартный приоритет |
| 3 | Новые | Низкий приоритет |

## Поля модели User

```python
class User(AbstractUser):
    is_premium = BooleanField(default=False)
    processing_priority = PositiveIntegerField(null=True, blank=True)
```

## Динамический расчет

Финальный приоритет рассчитывается на основе:
- Статус premium пользователя
- Длительность видео (короткие +1, длинные -1)
- Активность пользователя (>50 видео +1)

## Management команда

```bash
# Установить premium статус
python manage.py set_user_priority username --premium --priority 8

# Убрать premium
python manage.py set_user_priority username --no-premium

# Проверить приоритет
python manage.py set_user_priority username
```

## Celery интеграция

```python
CELERY_TASK_ROUTES = {
    'apps.videos.tasks.process_video_async': {
        'queue': 'video_processing',
    },
}

CELERY_TASK_DEFAULT_PRIORITY = 5
```

## Сервис PriorityManager

**Файл:** `apps/videos/services/priority_manager.py`

Методы:
- `get_user_priority()` - расчет приоритета
- `get_base_priority()` - базовый приоритет
- `estimate_queue_position()` - позиция в очереди

## Производительность

- Premium пользователи: < 5 минут ожидания
- Обычные пользователи: 15-30 минут
- Новые пользователи: 30-60 минут