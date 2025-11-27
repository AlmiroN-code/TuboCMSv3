# Аудит шаблонов TubeCMS v3

**Дата аудита:** 27.11.2025  
**Статус:** Критические ошибки исправлены ✅

---

## Исправленные ошибки ✅

| # | Проблема | Файл | Статус |
|---|----------|------|--------|
| 1 | Незакрытый тег `<html>` | base.html | ✅ Исправлено |
| 2 | Дублирование modal-container | base.html | ✅ Исправлено |
| 3 | Опечатка `x-swap` → `hx-swap` | base.html | ✅ Исправлено |
| 4 | Перепутаны метки Views/Videos | profile.html | ✅ Исправлено |
| 5 | Опечатка "Login in sustem" | login.html | ✅ Исправлено |
| 6 | Неправильный URL `users:profile` | playlist_detail.html | ✅ Исправлено |
| 7 | Неправильный URL `users:profile` | public_playlists.html | ✅ Исправлено |
| 8 | Неправильный URL `users:profile` | search_results.html | ✅ Исправлено |
| 9 | Неправильный URL `videos:category` | search_results.html | ✅ Исправлено |
| 10 | Шрифты в конце body | base.html | ✅ Перенесено в head |
| 11 | Кнопка Edit без функционала | profile.html | ✅ Исправлено |
| 12 | Кнопка Create playlist без ссылки | profile.html | ✅ Исправлено |
| 13 | Кнопка Share без функционала | actions.html | ✅ Добавлен shareVideo() |
| 14 | Отсутствие aria-labels | base.html | ✅ Добавлено |

---

## Критические ошибки (были)

### 1. base.html - Незакрытый тег HTML
**Файл:** `templates/base.html`
**Строка:** 8
**Проблема:** Отсутствует закрывающая угловая скобка в теге `<html>`
```html
<!-- ОШИБКА -->
<html lang="{% current_language %}"

<!-- ИСПРАВЛЕНИЕ -->
<html lang="{% current_language %}">
```

### 2. base.html - Дублирование modal-container
**Файл:** `templates/base.html`
**Проблема:** `modal-container` объявлен дважды в конце файла
```html
<!-- Первое объявление (строка ~100) -->
<div id="modal-container"></div>

<!-- Второе объявление (в конце) -->
<div id="modal-container" class="modal-overlay"></div>
```
**Решение:** Удалить одно из объявлений, оставить с классом `modal-overlay`

### 3. base.html - Опечатка в hx-swap
**Файл:** `templates/base.html`
**Строка:** ~50
**Проблема:** Опечатка `x-swap` вместо `hx-swap`
```html
<!-- ОШИБКА -->
hx-trigger="load, every 30s" x-swap="innerHTML"

<!-- ИСПРАВЛЕНИЕ -->
hx-trigger="load, every 30s" hx-swap="innerHTML"
```

### 4. profile.html - Перепутаны метки статистики
**Файл:** `templates/users/profile.html`
**Проблема:** Метки "Views" и "Videos" перепутаны местами
```html
<!-- ОШИБКА -->
<span class="stat-number">{{ profile_user.videos_count }}</span>
<span class="stat-label">{% trans 'Views' %}</span>  <!-- Должно быть Videos -->
...
<span class="stat-number">{{ profile_user.total_views|format_views }}</span>
<span class="stat-label">{% trans 'Videos' %}</span>  <!-- Должно быть Views -->
```

### 5. login.html - Опечатка в тексте
**Файл:** `templates/users/login.html`
**Проблема:** "Login in sustem" вместо "Login to system"
```html
<!-- ОШИБКА -->
<h2>Login in sustem</h2>

<!-- ИСПРАВЛЕНИЕ -->
<h2>Login to system</h2>
```

---

## Проблемы юзабилити и UX

### 6. video_card.html - Избыточные HTMX-запросы при загрузке
**Файл:** `templates/partials/video_card.html`
**Проблема:** Каждая карточка видео делает 3 HTMX-запроса при загрузке страницы
```html
<div class="watch-later-mount" hx-get="..." hx-trigger="load">
<div class="favorite-mount" hx-get="..." hx-trigger="load">
<div class="playlist-mount" hx-get="..." hx-trigger="load">
```
**Влияние:** При 20 видео на странице = 60 дополнительных запросов
**Решение:** Передавать состояние кнопок через контекст шаблона, а не через отдельные запросы

### 7. playlist_detail.html - Неправильный URL профиля
**Файл:** `templates/videos/playlist_detail.html`
**Проблема:** Используется несуществующий URL `users:profile`
```html
<!-- ОШИБКА -->
<a href="{% url 'users:profile' username=playlist.user.username %}">

<!-- ИСПРАВЛЕНИЕ -->
<a href="{% url 'members:profile' username=playlist.user.username %}">
```

### 8. public_playlists.html - Аналогичная ошибка URL
**Файл:** `templates/videos/public_playlists.html`
```html
<!-- ОШИБКА -->
<a href="{% url 'users:profile' username=playlist.user.username %}">
```

### 9. search_results.html - Неправильные URL
**Файл:** `templates/core/htmx/search_results.html`
**Проблемы:**
```html
<!-- ОШИБКА 1 -->
<a href="{% url 'users:profile' username=user.username %}">
<!-- Должно быть members:profile -->

<!-- ОШИБКА 2 -->
<a href="{% url 'videos:category' slug=category.slug %}">
<!-- Должно быть category:videos -->
```

### 10. Смешение языков в интерфейсе
**Файлы:** Множество шаблонов
**Проблема:** Часть текстов на русском, часть на английском без использования i18n
- `favorites.html` - полностью на русском без `{% trans %}`
- `playlists.html` - полностью на русском без `{% trans %}`
- `playlist_detail.html` - на русском без `{% trans %}`
- `playlists_modal.html` - на русском без `{% trans %}`

**Решение:** Обернуть все тексты в `{% trans %}` или `{% trans_custom %}`

---

## Проблемы безопасности

### 11. CSRF в JavaScript
**Файл:** `templates/videos/htmx/favorite_button.html`, `watch_later_button.html`
**Проблема:** Использование `request.COOKIES.csrftoken` напрямую
```html
hx-headers='{"X-CSRFToken": "{{ request.COOKIES.csrftoken }}"}'
```
**Риск:** Cookie может быть недоступен если установлен HttpOnly
**Решение:** Использовать `{% csrf_token %}` или meta-тег

### 12. XSS в ads/banner.html
**Файл:** `templates/ads/banner.html`
**Проблема:** HTML-контент выводится без экранирования
```html
{{ banner.html_content|safe }}
```
**Риск:** Если админ добавит вредоносный HTML, он выполнится
**Решение:** Валидация HTML на стороне сервера перед сохранением

---

## Проблемы производительности

### 13. Загрузка шрифтов в конце body
**Файл:** `templates/base.html`
**Проблема:** Google Fonts и Font Awesome загружаются в конце `<body>` вместо `<head>`
```html
<!-- В конце body - НЕПРАВИЛЬНО -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Roboto..." rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
```
**Влияние:** FOUT (Flash of Unstyled Text), задержка отображения иконок
**Решение:** Переместить в `<head>`

### 14. Отсутствие lazy loading для аватаров
**Файлы:** `profile.html`, `comments_list.html`, `notifications.html`
**Проблема:** Изображения аватаров загружаются сразу
**Решение:** Добавить `loading="lazy"` для изображений ниже fold

### 15. N+1 запросы в playlist_detail.html
**Файл:** `templates/users/profile.html`
**Проблема:** В табе playlists
```html
{% if playlist.videos.first %}
    <img src="{{ playlist.videos.first.poster.url }}"
```
**Влияние:** Каждый плейлист делает отдельный запрос к videos
**Решение:** Использовать `prefetch_related` во view

---

## Проблемы консистентности

### 16. Разные стили пагинации
**Файлы:** 
- `partials/pagination.html` - базовый стиль
- `community.html` - расширенный с ellipsis
- `notifications.html` - копия community
- `models/list.html` - Bootstrap-стиль

**Решение:** Унифицировать пагинацию, использовать один partial

### 17. Inline стили в шаблонах
**Файлы:** `playlist_detail.html`, `playlist_create.html`, `playlist_edit.html`, `report.html`, `notifications.html`, `public_playlists.html`
**Проблема:** Стили определены в `{% block extra_css %}` вместо base.css
**Нарушение:** Правило проекта - все стили в `static/css/base.css`

### 18. Дублирование JavaScript для тегов
**Файлы:** `upload.html`, `edit.html`
**Проблема:** Идентичный код управления тегами дублируется
**Решение:** Вынести в отдельный JS-файл или partial

---

## Отсутствующий функционал

### 19. Кнопка "Share" не работает
**Файл:** `templates/videos/htmx/actions.html`
```html
<button class="action-btn share-btn">
    <i class="fas fa-share"></i>
    <span>Share</span>
</button>
```
**Проблема:** Нет обработчика события

### 20. Кнопка "Edit" в профиле без функционала
**Файл:** `templates/users/profile.html`
```html
<button class="btn btn--secondary edit-btn">
    {% trans 'Edit' %}
</button>
```
**Проблема:** Кнопка ничего не делает

### 21. Кнопка "Create playlist" без ссылки
**Файл:** `templates/users/profile.html`
```html
<button class="btn btn--primary">
    {% trans 'Create playlist' %}
</button>
```
**Проблема:** Должна быть ссылка на `videos:playlist_create`

---

## Проблемы доступности (a11y)

### 22. Отсутствие aria-labels
**Файлы:** Большинство кнопок без текста
```html
<button class="theme-toggle" id="themeToggle">
    <i class="fas fa-moon"></i>
</button>
```
**Решение:** Добавить `aria-label="Toggle theme"`

### 23. Отсутствие alt для изображений
**Файлы:** Некоторые `<img>` без alt или с пустым alt
**Решение:** Добавить осмысленные alt-тексты

### 24. Низкий контраст в некоторых элементах
**Проблема:** Текст `text-secondary` может иметь недостаточный контраст
**Решение:** Проверить WCAG AA compliance

---

## Рекомендации по улучшению

### 25. Добавить skeleton loading
**Где:** video_card.html, profile.html
**Зачем:** Улучшить perceived performance

### 26. Добавить infinite scroll
**Где:** Списки видео, комментарии
**Зачем:** Улучшить UX на мобильных

### 27. Добавить toast notifications
**Где:** После HTMX-действий
**Текущее:** Уведомления есть в JS, но не всегда показываются

### 28. Добавить подтверждение действий
**Где:** Удаление из избранного, отписка
**Зачем:** Предотвратить случайные действия

### 29. Улучшить мобильную навигацию
**Проблема:** Sidebar не адаптирован для мобильных
**Решение:** Добавить hamburger menu

### 30. Добавить breadcrumbs
**Где:** Страницы категорий, тегов, плейлистов
**Зачем:** Улучшить навигацию

---

## Приоритеты исправлений

### Критические (исправить немедленно):
1. Незакрытый тег `<html>` в base.html
2. Опечатка `x-swap` вместо `hx-swap`
3. Неправильные URL (`users:profile` → `members:profile`)

### Высокий приоритет:
4. Перепутанные метки статистики в profile.html
5. Дублирование modal-container
6. Избыточные HTMX-запросы в video_card.html

### Средний приоритет:
7. Смешение языков без i18n
8. Inline стили вместо base.css
9. Дублирование JS-кода

### Низкий приоритет:
10. Улучшения доступности
11. Skeleton loading
12. Infinite scroll
