# HLS/DASH адаптивный стриминг

## Описание

Система поддерживает адаптивный битрейт стриминг через протоколы HLS и DASH для оптимальной доставки видео.

## Протоколы

### HLS (HTTP Live Streaming)
- Сегменты: TS формат, ~10 секунд
- Манифест: M3U8 плейлист
- Широкая поддержка браузеров

### DASH (Dynamic Adaptive Streaming)  
- Сегменты: MP4 формат, ~4 секунды
- Манифест: MPD (XML)
- Быстрое переключение качества

## Структура файлов

```
media/streams/
├── hls/{video_id}/
│   ├── 360p/playlist.m3u8
│   ├── 720p/playlist.m3u8
│   └── master.m3u8
└── dash/{video_id}/
    ├── 360p/manifest.mpd
    ├── 720p/manifest.mpd
    └── master.mpd
```

## Адаптивный плеер

**Файл:** `templates/videos/player_adaptive.html`

**Функции:**
- Автоматический выбор HLS/DASH/MP4
- Меню выбора качества
- Переключение между протоколами
- Fallback на MP4

**Использование:**
```django
{% include 'videos/player_adaptive.html' %}
```

## Генерация стримов

**Все видео:**
```bash
python manage.py generate_streams
```

**Конкретное видео:**
```bash
python manage.py generate_streams --video-id 123
```

**Только HLS или DASH:**
```bash
python manage.py generate_streams --stream-type hls
python manage.py generate_streams --stream-type dash
```

## Модель данных

```python
class VideoStream(TimeStampedModel):
    video = ForeignKey(Video)
    stream_type = CharField()  # hls/dash
    profile = ForeignKey(VideoEncodingProfile)
    manifest_path = CharField()
    segment_count = PositiveIntegerField()
    is_ready = BooleanField()
```

## Админ-панель

Просмотр стримов: `/admin/videos/videostream/`
