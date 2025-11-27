# Система мониторинга и алертов

## Описание

Система мониторинга отслеживает состояние инфраструктуры обработки видео и отправляет уведомления администраторам.

## Типы алертов

### 1. Размер очереди
- Предупреждение: 50+ задач
- Критический: 100+ задач

### 2. Процент ошибок
- Ошибка: 20%+ неудачных обработок за час

### 3. Недоступность FFmpeg
- Критический: FFmpeg не найден

### 4. Место на диске
- Предупреждение: 85%+ использования
- Критический: 95%+ использования

### 5. Время обработки
- Предупреждение: 30+ минут среднее время

## Модели данных

```python
class AlertRule(TimeStampedModel):
    name = CharField(max_length=100)
    alert_type = CharField(max_length=20)
    threshold_value = FloatField()
    severity = CharField(max_length=10)
    is_active = BooleanField(default=True)
    email_recipients = TextField(blank=True)
    webhook_url = URLField(blank=True)

class Alert(TimeStampedModel):
    rule = ForeignKey(AlertRule)
    status = CharField(max_length=15)  # active/acknowledged/resolved
    message = TextField()
    current_value = FloatField()
    email_sent = BooleanField(default=False)
    webhook_sent = BooleanField(default=False)
```

## Создание правил

**Через админку:**
- `/admin/videos/alertrule/` - создание правил
- `/admin/videos/alert/` - просмотр алертов

**Через команду:**
```bash
python manage.py create_default_alerts
```

## Уведомления

### Email
Настройка в settings.py:
```python
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

### Webhook (Slack, Discord)
Добавить URL в поле webhook_url правила алерта.

## Celery интеграция

Проверка каждые 5 минут:
```python
CELERY_BEAT_SCHEDULE = {
    'check_alert_rules': {
        'task': 'apps.videos.tasks.check_alert_rules',
        'schedule': 300.0,
    },
}
```

## Сервис AlertService

**Файл:** `apps/videos/services/alert_service.py`

Методы:
- `check_all_rules()` - проверка всех правил
- `get_system_health()` - состояние системы
- `get_active_alerts()` - активные алерты
- `acknowledge_alert()` - подтверждение алерта
