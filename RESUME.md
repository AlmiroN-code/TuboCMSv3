# RESUME.md - TubeCMS v3

**Дата создания:** 25 ноября 2025  
**Версия проекта:** Django 5.2.8 + HTMX 1.9.10  
**Тип проекта:** Видеохостинг платформа

---

## ПРАВИЛА РАЗРАБОТКИ (ОБЯЗАТЕЛЬНЫ К ИСПОЛНЕНИЮ)

### 1. Никаких несанкционированных изменений
- Не добавлять, не удалять, не модифицировать код без прямого запроса
- При неопределённости — спрашивать уточнение

### 2. Планирование перед действием
- Составлять чёткий пошаговый план
- Перечислять затрагиваемые файлы
- Запрашивать подтверждение перед реализацией

### 3. Документация
- Вся документация (кроме inline комментариев) — только в `/docs/`
- Никаких README в подпапках без разрешения

### 4. CSS стили
- Все стили — только в `static/css/base.css`
- Запрещены новые CSS файлы без разрешения
- Запрещены inline стили в HTML без разрешения

### 5. Предотвращение дублирования
- Перед созданием проверять существующий код
- Переиспользовать существующую логику
- Предлагать расширение вместо дублирования

### 6. Принцип "Не навреди"
- При неуверенности — спрашивать
- Не менять код по предположениям
- Не трогать несвязанный код

### 7. Общение
- Кратко, технически точно, на русском
- Только необходимая информация

---

## СТРУКТУРА ПРОЕКТА

```
TuboCMSv3/
├── apps/                           # Django приложения
│   ├── core/                       # Центральное приложение
│   ├── users/                      # Пользователи
│   ├── videos/                     # Видео (основное)
│   ├── comments/                   # Комментарии
│   ├── models/                     # Модели/перформеры
│   ├── ads/                        # Реклама
│   └── localization/               # Локализация
├── config/                         # Конфигурация Django
│   ├── settings/                   # Настройки (base, dev, prod)
│   ├── urls.py                     # Корневые URL
│   ├── wsgi.py                     # WSGI
│   ├── asgi.py                     # ASGI
│   └── celery.py                   # Celery конфигурация
├── templates/                      # HTML шаблоны
│   ├── base.html                   # Базовый шаблон
│   ├── partials/                   # Переиспользуемые части
│   ├── core/                       # Шаблоны core
│   ├── videos/                     # Шаблоны videos
│   ├── users/                      # Шаблоны users
│   └── comments/                   # Шаблоны comments
├── static/                         # Статические файлы
│   ├── css/
│   │   └── base.css                # ВСЕ СТИЛИ ЗДЕСЬ
│   └── js/
│       └── htmx-handlers.js        # HTMX обработчики
├── media/                          # Загружаемые файлы
├── docs/                           # ВСЯ ДОКУМЕНТАЦИЯ ЗДЕСЬ
├── requirements/                   # Зависимости
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── manage.py                       # Django CLI
├── README.md                       # Основное описание
└── RESUME.md                       # Этот файл (правила + структура)
```

---

## КЛЮЧЕВЫЕ КОМПОНЕНТЫ

### 1. ПРИЛОЖЕНИЕ: apps/core/

**Назначение:** Центральное приложение для общих компонентов

**Файлы:**
- `apps/core/models.py` - Модели: Category, Tag, SiteSettings, SEOSettings
- `apps/core/views.py` - Views: home, search, categories, search_dropdown
- `apps/core/urls.py` - URL маршруты
- `apps/core/middleware.py` - 5 кастомных middleware (Performance, Cache, Compression, DB, RateLimit)
- `apps/core/context_processors.py` - Глобальные контекст-процессоры
- `apps/core/services.py` - CacheService, VideoStatsService, SearchService
- `apps/core/managers.py` - CategoryManager, TagManager
- `apps/core/admin.py` - Админка для моделей

**Ключевые паттерны:**
- Singleton для SiteSettings/SEOSettings (только один активный)
- Автоматическая инвалидация кэша при save()
- Кастомные менеджеры для оптимизации

### 2. ПРИЛОЖЕНИЕ: apps/videos/

**Назначение:** Основное приложение для видео контента

**Структура:**
```
apps/videos/
├── models.py                    # Video, VideoFile, Rating, WatchLater
├── models_encoding.py           # VideoEncodingProfile
├── models_favorites.py          # Favorite, Playlist, PlaylistVideo
├── views.py                     # Основные views
├── rating_views.py              # Рейтинг views
├── views_favorites.py           # Избранное views
├── htmx/
│   └── views.py                 # HTMX-специфичные views
├── managers.py                  # VideoManager с оптимизацией
├── services.py                  # VideoProcessingService, VideoViewService
├── services_encoding.py         # EncodingService
├── tasks.py                     # Celery задачи
├── forms.py                     # VideoUploadForm, VideoEditForm
├── urls.py                      # URL маршруты
└── admin.py                     # Админка
```

**Ключевые файлы:**
- `apps/videos/models.py` - Video модель с 17 индексами
- `apps/videos/managers.py` - VideoQuerySet с методами: published(), with_related(), trending()
- `apps/videos/htmx/views.py` - 10+ HTMX endpoints
- `apps/videos/tasks.py` - process_video_async, process_pending_videos

**Ключевые паттерны:**
- Разделение на модули по функциональности
- Отдельная папка htmx/ для HTMX views
- Оптимизированные QuerySet (select_related, prefetch_related)
- 17 индексов БД для производительности

### 3. ПРИЛОЖЕНИЕ: apps/users/

**Назначение:** Кастомная модель пользователя и профили

**Файлы:**
- `apps/users/models.py` - User, UserProfile, Subscription, Friendship, Notification
- `apps/users/views.py` - Профиль, подписки, уведомления
- `apps/users/forms.py` - Регистрация, логин, редактирование
- `apps/users/managers.py` - UserManager, SubscriptionManager, NotificationManager
- `apps/users/urls.py` - URL маршруты
- `apps/users/member_urls.py` - URL для профилей пользователей

**Ключевые особенности:**
- Расширенная модель User (AbstractUser)
- Система дружбы (Friendship)
- Уведомления с типами
- Подписки между пользователями
- Система приватности профиля (UserProfile):
  - `show_videos_publicly` (default: True) - видео видны всем
  - `show_friends_publicly` (default: True) - друзья видны всем
  - `show_favorites_publicly` (default: False) - избранное скрыто
  - `show_watch_later_publicly` (default: False) - "посмотреть позже" скрыто
  - Subscriptions/Notifications - всегда приватны (только владелец)
  - Playlists - другим видны только публичные
  - About - всегда видна всем

### 4. ПРИЛОЖЕНИЕ: apps/comments/

**Назначение:** Система комментариев

**Файлы:**
- `apps/comments/models.py` - Comment с поддержкой вложенности
- `apps/comments/views.py` - CRUD комментариев
- `apps/comments/urls.py` - URL маршруты

**Ключевые особенности:**
- Вложенные комментарии (parent/replies)
- Лайки комментариев

### 5. ПРИЛОЖЕНИЕ: apps/models/

**Назначение:** Модели/перформеры

**Файлы:**
- `apps/models/models.py` - Model, ModelVideo (through table)
- `apps/models/views.py` - Список, детали моделей
- `apps/models/urls.py` - URL маршруты

### 6. ПРИЛОЖЕНИЕ: apps/ads/

**Назначение:** Система рекламы

**Файлы:**
- `apps/ads/models.py` - Advertisement
- `apps/ads/templatetags/ads_tags.py` - Template tags для рендеринга
- `apps/ads/admin.py` - Админка

### 7. ПРИЛОЖЕНИЕ: apps/localization/

**Назначение:** Управление переводами

**Файлы:**
- `apps/localization/models.py` - LocalizationSettings, Rosetta (proxy)
- `apps/localization/admin.py` - Админка с редиректом на Rosetta

---

## HTMX АРХИТЕКТУРА

### Паттерн организации HTMX

**1. Отдельные views для HTMX:**
- `apps/videos/htmx/views.py` - HTMX endpoints
- Префикс `htmx/` в URL
- Суффикс `_htmx` в именах URL

**2. Отдельные шаблоны для HTMX:**
```
templates/videos/htmx/
├── favorite_button.html         # Кнопка избранного
├── watch_later_button.html      # Кнопка "Посмотреть позже"
├── rating_widget.html           # Виджет рейтинга
├── list_partial.html            # Частичный список
└── ... (14 шаблонов всего)
```

**3. JavaScript обработчики:**
- `static/js/htmx-handlers.js` - 600+ строк
- CSRF токены для всех запросов
- Обработка JSON ответов
- Система уведомлений
- Обработка ошибок

**Ключевые HTMX атрибуты:**
```html
hx-get="{% url 'core:search_dropdown' %}"
hx-target="#search-dropdown-results"
hx-trigger="keyup changed delay:500ms"
hx-swap="innerHTML"
hx-indicator="#search-loading"
```

**ВАЖНО:** Все HTMX views возвращают HTML фрагменты, не полные страницы.

---

## БАЗОВЫЙ ШАБЛОН

**Файл:** `templates/base.html`

**Ключевые компоненты:**
1. HTMX подключение (unpkg.com)
2. CSRF токен в meta
3. Поиск с HTMX автодополнением
4. Уведомления с автообновлением (каждые 30с)
5. Темизация (light/dark)
6. SEO meta теги
7. Аналитика (GA, Яндекс.Метрика, Facebook Pixel, VK Pixel)

**ВАЖНО:** Не модифицировать без необходимости - используется всеми страницами.

---

## CSS АРХИТЕКТУРА

**Файл:** `static/css/base.css` (2000+ строк)

**Структура:**
1. Сброс стилей
2. CSS переменные для темизации
3. Базовые элементы
4. Компоненты (header, search, video-grid, etc.)
5. Адаптивность (5 breakpoints)

**CSS переменные:**
```css
:root {
    --accent-color: #8AA398;
    --bg-primary: #252B30;
    --text-primary: #fff;
}

.light-theme {
    --bg-primary: #fff;
    --text-primary: #434343;
}
```

**ПРАВИЛО:** Все новые стили добавлять ТОЛЬКО в base.css.

---

## МОДЕЛИ И БД

### Ключевые модели:

**1. Video (apps/videos/models.py)**
- 17 индексов для оптимизации
- Поля: title, slug, description, status, views_count
- Связи: created_by (User), category (Category), tags (M2M)
- JSON поле: converted_files

**2. User (apps/users/models.py)**
- Расширяет AbstractUser
- Дополнительные поля: avatar, bio, birth_date, location, country, gender
- Статистика: subscribers_count, videos_count, total_views

**3. Category (apps/core/models.py)**
- Singleton pattern для активных
- Автоинвалидация кэша при save()

**4. Rating (apps/videos/models.py)**
- Уникальность: либо user, либо ip_address
- Кастомная валидация в clean()

### Индексы (Video):
```python
indexes = [
    models.Index(fields=["status", "created_at"]),
    models.Index(fields=["status", "is_featured", "created_at"]),
    models.Index(fields=["views_count", "created_at"]),
    models.Index(fields=["title"]),
    models.Index(fields=["slug"]),
    # ... всего 17 индексов
]
```

---

## ОПТИМИЗАЦИЯ ПРОИЗВОДИТЕЛЬНОСТИ

### 1. Кэширование

**CacheService (apps/core/services.py):**
```python
SHORT_TIMEOUT = 300      # 5 минут
MEDIUM_TIMEOUT = 1800    # 30 минут
LONG_TIMEOUT = 3600      # 1 час
VERY_LONG_TIMEOUT = 86400 # 24 часа
```

**Методы:**
- `get_categories_cached()` - кэш категорий
- `get_site_settings_cached()` - кэш настроек
- `get_seo_settings_cached()` - кэш SEO

**Автоинвалидация:**
```python
def save(self, *args, **kwargs):
    super().save(*args, **kwargs)
    cache.delete("site_settings_active")
```

### 2. Оптимизация запросов

**VideoManager (apps/videos/managers.py):**
```python
def with_related(self):
    return self.select_related("created_by", "category").prefetch_related(
        "tags", "encoded_files__profile", "ratings__user"
    )
```

**Использование:**
```python
# Плохо - N+1 запросов
videos = Video.objects.all()

# Хорошо - оптимизировано
videos = Video.objects.published().with_related()
```

### 3. Middleware

**5 кастомных middleware (apps/core/middleware.py):**
1. `PerformanceMiddleware` - мониторинг времени запросов
2. `CacheControlMiddleware` - Cache-Control заголовки
3. `CompressionMiddleware` - подсказки для сжатия
4. `DatabaseOptimizationMiddleware` - мониторинг SQL запросов
5. `RateLimitMiddleware` - ограничение запросов (100/мин для анонимов)

---

## CELERY ЗАДАЧИ

**Файл:** `apps/videos/tasks.py`

**Задачи:**
1. `process_video_async` - асинхронная обработка видео
2. `process_pending_videos` - обработка ожидающих (каждую минуту)
3. `cleanup_old_videos` - очистка старых черновиков (ежедневно в 03:00)
4. `send_processing_complete_notification` - уведомление о завершении

**Celery Beat расписание:**
```python
CELERY_BEAT_SCHEDULE = {
    'videos_process_pending': {
        'task': 'apps.videos.tasks.process_pending_videos',
        'schedule': 60.0,
    },
    'videos_cleanup_old': {
        'task': 'apps.videos.tasks.cleanup_old_videos',
        'schedule': crontab(minute=0, hour=3),
    },
}
```

---

## НАСТРОЙКИ

### Структура:
```
config/settings/
├── base.py           # Базовые настройки
├── development.py    # Разработка (SQLite, Celery eager)
└── production.py     # Продакшн (PostgreSQL, Redis)
```

**Development:**
- SQLite
- Celery в eager режиме (синхронно)
- Email в консоль
- DEBUG = True

**Production:**
- PostgreSQL
- Redis кэш
- Переменные окружения (python-decouple)
- Усиленная безопасность (SSL, HSTS)

---

## ПРЕДУПРЕЖДЕНИЯ О ДУБЛИРОВАНИИ

### ❌ НЕ СОЗДАВАТЬ:

1. **Новые CSS файлы** - использовать base.css
2. **Дублирующие views** - проверять существующие
3. **Дублирующие сервисы** - использовать CacheService, VideoStatsService
4. **Дублирующие менеджеры** - расширять существующие
5. **Inline стили** - только в base.css
6. **Документацию вне /docs/** - только в /docs/

### ✅ ПЕРЕИСПОЛЬЗОВАТЬ:

1. **VideoManager.with_related()** - для оптимизации запросов
2. **CacheService** - для кэширования
3. **TimeStampedModel** - базовая модель с created_at/updated_at
4. **HTMX шаблоны** - расширять существующие
5. **Middleware** - использовать существующие

---

## АЛГОРИТМЫ И РЕШЕНИЯ

### 1. HTMX Partial Swap

**Реализация:**
```python
# View возвращает HTML фрагмент
def favorite_toggle(request, slug):
    # Логика toggle
    return render(request, "videos/htmx/favorite_button.html", context)
```

```html
<!-- HTMX заменяет элемент -->
<div hx-post="{% url 'videos:htmx_favorite' video.slug %}"
     hx-target="#fav-btn-{{ video.id }}"
     hx-swap="outerHTML">
</div>
```

### 2. Атомарное увеличение счетчиков

**Реализация:**
```python
from django.db.models import F

def increment_views(self):
    Video.objects.filter(pk=self.pk).update(views_count=F('views_count') + 1)
    self.refresh_from_db()
```

**Причина:** Избегаем race conditions при конкурентных запросах.

### 3. Singleton для настроек

**Реализация:**
```python
def save(self, *args, **kwargs):
    if self.is_active:
        SiteSettings.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
    super().save(*args, **kwargs)
```

**Причина:** Только один активный экземпляр настроек.

### 4. Debounce для поиска

**Реализация:**
```html
<input hx-get="{% url 'core:search_dropdown' %}"
       hx-trigger="keyup changed delay:500ms">
```

**Причина:** Оптимизация - не отправлять запрос на каждое нажатие клавиши.

---

## КОНТРОЛЬНЫЙ СПИСОК ПЕРЕД ИЗМЕНЕНИЯМИ

### Перед созданием нового компонента:

- [ ] Проверил существующий код в соответствующем приложении
- [ ] Проверил managers.py на наличие похожих методов
- [ ] Проверил services.py на наличие похожей логики
- [ ] Проверил HTMX views на наличие похожих endpoints
- [ ] Проверил шаблоны на наличие похожих компонентов
- [ ] Составил план изменений
- [ ] Запросил подтверждение

### Перед добавлением стилей:

- [ ] Проверил base.css на наличие похожих стилей
- [ ] Использую CSS переменные для темизации
- [ ] Не создаю новый CSS файл
- [ ] Не использую inline стили

### Перед добавлением документации:

- [ ] Размещаю в /docs/
- [ ] Не создаю README в подпапках

---

## ТЕХНОЛОГИЧЕСКИЙ СТЕК

**Backend:**
- Django 5.2.8
- Celery 5.3.4
- Redis 5.0.1
- PostgreSQL (prod) / SQLite (dev)

**Frontend:**
- HTMX 1.9.10
- Vanilla JavaScript
- CSS3 (переменные, Grid, Flexbox)
- Font Awesome 6.4.0

**Инфраструктура:**
- WhiteNoise 6.6.0
- Gunicorn 21.2.0
- FFmpeg (обработка видео)
- Pillow 10.1.0

---

## КОМАНДЫ

```bash
# Разработка
python manage.py runserver
python manage.py makemigrations
python manage.py migrate

# Celery
celery -A config worker -l info
celery -A config beat -l info

# Тесты
pytest
pytest --cov=apps

# Статика
python manage.py collectstatic

# Переводы
python manage.py makemessages -l ru
python manage.py compilemessages
```

---

**КОНЕЦ RESUME.md**

*Этот файл является обязательным референсом для всех будущих изменений проекта. Неукоснительно и всегда следовать этим правилам.*


---

## HLS/DASH АДАПТИВНЫЙ СТРИМИНГ

**Дата реализации:** 26 ноября 2025  
**Статус:** ✅ COMPLETED

### Назначение

Адаптивный битрейт стриминг для оптимальной доставки видео контента с автоматическим переключением качества.

### Протоколы

**HLS (HTTP Live Streaming):**
- Формат сегментов: TS (Transport Stream)
- Манифест: M3U8 playlist
- Длительность сегмента: 10 секунд
- Широкая поддержка браузеров

**DASH (Dynamic Adaptive Streaming):**
- Формат сегментов: MP4
- Манифест: MPD (XML)
- Длительность сегмента: 4 секунды
- Быстрое переключение качества

### Компоненты

**Модель (apps/videos/models.py):**
- `VideoStream` - информация о сгенерированных стримах

**Сервисы:**
- `HLSService` (apps/videos/services/hls_service.py)
- `DASHService` (apps/videos/services/dash_service.py)

**Плеер (templates/videos/player_adaptive.html):**
- Автоматический выбор HLS/DASH
- Меню выбора качества
- Переключение между протоколами
- Fallback на MP4

**Management команда:**
- `generate_streams` - генерация стримов для видео

### Структура файлов

```
media/streams/
├── hls/{video_id}/
│   ├── 360p/
│   │   ├── playlist.m3u8
│   │   └── segment_*.ts
│   ├── 720p/
│   │   ├── playlist.m3u8
│   │   └── segment_*.ts
│   └── master.m3u8
└── dash/{video_id}/
    ├── 360p/
    │   ├── manifest.mpd
    │   ├── init.mp4
    │   └── segment_*.m4s
    ├── 720p/
    │   ├── manifest.mpd
    │   ├── init.mp4
    │   └── segment_*.m4s
    └── master.mpd
```

### Использование

**Генерация стримов:**
```bash
# Все видео
python manage.py generate_streams

# Конкретное видео
python manage.py generate_streams --video-id 123

# Только HLS или DASH
python manage.py generate_streams --stream-type hls
python manage.py generate_streams --stream-type dash

# Принудительная регенерация
python manage.py generate_streams --force
```

**Тестирование:**
```bash
python test_streaming.py
```

**В шаблонах:**
```django
{% if video.streams.filter(is_ready=True).exists %}
    {% include 'videos/player_adaptive.html' %}
{% endif %}
```

### Библиотеки плеера

- **hls.js** - HLS плеер для браузеров
- **dash.js** - DASH плеер

Подключаются автоматически в `player_adaptive.html`

### Функции плеера

- ✅ Автоматический выбор протокола (HLS → DASH → MP4)
- ✅ Адаптивное переключение качества
- ✅ Ручной выбор качества
- ✅ Переключение между HLS/DASH
- ✅ Отображение текущего разрешения
- ✅ Fallback на стандартный MP4
- ✅ Отслеживание просмотров

### Админ-панель

- Просмотр стримов: `/admin/videos/videostream/`
- Фильтры по типу и статусу
- Информация о сегментах и размере

### Документация

Полная документация: `docs/STREAMING.md`

---

## СИСТЕМА АЛЕРТОВ (ALERTS)

**Дата реализации:** 26 ноября 2025  
**Статус:** ✅ COMPLETED

### Назначение

Система мониторинга и оповещения для отслеживания состояния инфраструктуры обработки видео.

### Компоненты

**Модели (apps/videos/models_alerts.py):**
- `AlertRule` - правила для алертов (пороги, типы, уведомления)
- `Alert` - экземпляры алертов (активные, подтвержденные, решенные)
- `SystemMetric` - метрики системы для исторического анализа

**Сервис (apps/videos/services/alert_service.py):**
- `AlertService` - проверка правил, отправка уведомлений, мониторинг здоровья системы

**Celery задача (apps/videos/tasks.py):**
- `check_alert_rules` - периодическая проверка (каждые 5 минут)

**Management команда:**
- `create_default_alerts` - создание дефолтных правил

### Типы алертов

1. **Queue Size** - размер очереди обработки
   - Warning: 50+ задач
   - Critical: 100+ задач

2. **Error Rate** - процент ошибок обработки (за последний час)
   - Error: 20%+ ошибок

3. **FFmpeg Unavailable** - недоступность FFmpeg
   - Critical: FFmpeg не найден

4. **Disk Space** - использование диска
   - Warning: 85%+ использования
   - Critical: 95%+ использования

5. **Processing Time** - среднее время обработки (за 24 часа)
   - Warning: 30+ минут

### Каналы уведомлений

- **Email** - настраивается список получателей
- **Webhook** - поддержка Slack, Discord, Microsoft Teams и др.

### Функции

- ✅ Мониторинг в реальном времени
- ✅ Настраиваемые пороги и уровни серьезности
- ✅ Автоматическое разрешение алертов
- ✅ Cooldown периоды (предотвращение спама)
- ✅ Админ-панель для управления
- ✅ Исторические метрики

### Использование

**Создание дефолтных правил:**
```bash
python manage.py create_default_alerts
```

**Тестирование:**
```bash
python test_alerts.py
```

**Настройка:**
- Админ-панель: `/admin/videos/alertrule/`
- Просмотр алертов: `/admin/videos/alert/`
- Метрики: `/admin/videos/systemmetric/`

**Программный доступ:**
```python
from apps.videos.services.alert_service import AlertService

service = AlertService()
health = service.get_system_health()
alerts = service.get_active_alerts()
```

### Документация

Полная документация: `docs/ALERTS.md`

### Celery Beat Schedule

```python
'check_alert_rules': {
    'task': 'apps.videos.tasks.check_alert_rules',
    'schedule': 300.0,  # каждые 5 минут
}
```

### Следующие шаги

1. Настроить email получателей в админке
2. Настроить webhook интеграции (Slack/Discord)
3. Протестировать email уведомления
4. Мониторить алерты в продакшене
