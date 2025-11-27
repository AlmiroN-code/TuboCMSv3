# Changelog

## [2.0.0] - 2025-11-26

### Added - Video Processing System 2.0

#### 1. Модульная архитектура
- Разделение на независимые сервисы (FFmpegWrapper, MetadataExtractor, ThumbnailGenerator, VideoEncoder)
- Улучшенная обработка ошибок и логирование
- Файлы: `apps/videos/services/`

#### 2. Система приоритетов
- Поля `is_premium` и `processing_priority` в модели User
- PriorityManager для расчета приоритетов
- Интеграция с Celery очередью
- Management команда `set_user_priority`

#### 3. Параллельное кодирование
- ThreadPoolExecutor с max_workers=2
- Ускорение до 2x при обработке нескольких профилей

#### 4. HLS/DASH стриминг
- Модель VideoStream
- Сервисы HLSService и DASHService
- Адаптивный плеер `player_adaptive.html`
- Management команда `generate_streams`

#### 5. Автоматическая очистка
- Удаление временных файлов при ошибках
- Cleanup в блоках except

#### 6. Проверка диска
- Проверка свободного места (минимум 1GB)
- Предотвращение ошибок "disk full"

#### 7. Метрики обработки
- Модель ProcessingMetric
- Сбор времени обработки, размеров файлов, битрейта
- Админ-панель для просмотра

#### 8. Система алертов
- Модели AlertRule, Alert, SystemMetric
- Мониторинг очереди, ошибок, диска, FFmpeg
- Email и webhook уведомления
- Celery задача каждые 5 минут

### Migration
- 0019: Добавлены поля приоритетов в User
- 0020: Добавлены модели алертов

### Documentation
- `docs/MODULAR_ARCHITECTURE.md`
- `docs/PRIORITY_QUEUE.md`
- `docs/PARALLEL_ENCODING.md`
- `docs/STREAMING.md`
- `docs/ERROR_CLEANUP.md`
- `docs/DISK_SPACE_CHECK.md`
- `docs/PROCESSING_METRICS.md`
- `docs/ALERTS.md`

---

## [Unreleased] - 2025-11-25

### Changed
- Обновлен Django с 5.0.1 до 5.2.8
- Установлен Django Unfold для админ-панели
- Добавлен WYSIWYG редактор Trix
- Добавлен выпадающий список языков в шапке