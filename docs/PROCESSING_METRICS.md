# Метрики обработки видео

## Описание

Система собирает детальные метрики каждой обработки видео для анализа производительности.

## Собираемые метрики

- Время обработки (секунды)
- Размер входного файла (байты)
- Размер выходного файла (байты)
- Битрейт видео
- Профиль кодирования
- Статус обработки (success/error)
- Сообщение об ошибке (если есть)

## Модель данных

```python
class ProcessingMetric(TimeStampedModel):
    video = ForeignKey(Video)
    profile = ForeignKey(VideoEncodingProfile)
    processing_time = FloatField()  # секунды
    input_file_size = BigIntegerField()  # байты
    output_file_size = BigIntegerField()  # байты
    bitrate = IntegerField()  # kbps
    status = CharField()  # success/error
    error_message = TextField()
```

## Использование

Метрики записываются автоматически при каждой обработке.

Просмотр в админке: `/admin/videos/processingmetric/`

## Анализ

- Средние времена обработки по профилям
- Статистика успешности
- Анализ производительности
- Выявление проблемных профилей