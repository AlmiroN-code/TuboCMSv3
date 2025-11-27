"""
Signals for video model.
Надёжный запуск обработки видео после сохранения.
"""
import logging

from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from .models import Video

logger = logging.getLogger(__name__)

# Храним старое значение файла перед сохранением
_old_temp_video_file = {}


@receiver(pre_save, sender=Video)
def video_pre_save(sender, instance, **kwargs):
    """Сохраняем старое значение temp_video_file перед сохранением."""
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            _old_temp_video_file[instance.pk] = (
                old_instance.temp_video_file.name
                if old_instance.temp_video_file
                else None
            )
        except sender.DoesNotExist:
            _old_temp_video_file[instance.pk] = None
    else:
        # Новый объект - используем временный ID
        instance._temp_signal_id = id(instance)
        _old_temp_video_file[instance._temp_signal_id] = None


@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    """
    Запуск обработки видео после сохранения.
    Видео сохраняется СРАЗУ, обработка идёт в фоне.
    """
    # Получаем старое значение файла
    if instance.pk:
        old_file = _old_temp_video_file.pop(instance.pk, None)
    elif hasattr(instance, "_temp_signal_id"):
        old_file = _old_temp_video_file.pop(instance._temp_signal_id, None)
    else:
        old_file = None

    # Новое значение файла
    new_file = instance.temp_video_file.name if instance.temp_video_file else None

    # Проверяем существование файла
    file_exists = False
    if instance.temp_video_file:
        try:
            file_exists = instance.temp_video_file.storage.exists(
                instance.temp_video_file.name
            )
        except Exception:
            try:
                import os
                file_exists = os.path.exists(instance.temp_video_file.path)
            except Exception:
                file_exists = False

    # Определяем нужно ли запускать обработку
    should_process = False
    
    # Условия для запуска обработки:
    if instance.processing_status in ["processing", "completed"]:
        # Уже обрабатывается или завершено - пропускаем
        pass
    elif created and new_file and file_exists:
        # Новое видео с файлом
        should_process = True
        logger.info(f"[SIGNAL] New video {instance.id} with file, starting processing")
    elif new_file and file_exists and old_file != new_file:
        # Файл изменился
        should_process = True
        logger.info(f"[SIGNAL] Video {instance.id} file changed, starting processing")
    elif new_file and file_exists and instance.processing_status == "pending":
        # Файл есть, но обработка не начиналась
        should_process = True
        logger.info(f"[SIGNAL] Video {instance.id} pending with file, starting processing")

    if should_process:
        # Запускаем обработку НАДЁЖНО
        _start_video_processing(instance)

    # Обновляем счётчик видео пользователя
    if created and instance.created_by:
        try:
            instance.created_by.videos_count += 1
            instance.created_by.save(update_fields=["videos_count"])
        except Exception as e:
            logger.warning(f"Failed to update video count: {e}")


def _start_video_processing(video):
    """
    Надёжный запуск обработки видео.
    Пробует несколько способов, гарантирует что задача будет поставлена в очередь.
    """
    video_id = video.id
    selected_profiles = getattr(video, "_selected_encoding_profiles", None)
    
    # Устанавливаем статус processing
    Video.objects.filter(pk=video_id).update(processing_status="processing")
    
    # Способ 1: Простой delay() - самый надёжный
    try:
        from .tasks import process_video_async
        process_video_async.delay(video_id, selected_profiles)
        logger.info(f"[SIGNAL] Task queued for video {video_id} via delay()")
        return
    except Exception as e:
        logger.warning(f"[SIGNAL] delay() failed for video {video_id}: {e}")
    
    # Способ 2: apply_async без приоритетов
    try:
        from .tasks import process_video_async
        process_video_async.apply_async(args=[video_id, selected_profiles])
        logger.info(f"[SIGNAL] Task queued for video {video_id} via apply_async()")
        return
    except Exception as e:
        logger.warning(f"[SIGNAL] apply_async() failed for video {video_id}: {e}")
    
    # Способ 3: Отложенный запуск через threading (fallback)
    try:
        import threading
        
        def delayed_task():
            import time
            import django
            time.sleep(1)  # Небольшая задержка
            django.db.connections.close_all()
            try:
                from .tasks import process_video_async
                process_video_async.delay(video_id, selected_profiles)
                logger.info(f"[SIGNAL] Task queued for video {video_id} via thread")
            except Exception as ex:
                logger.error(f"[SIGNAL] Thread task failed for video {video_id}: {ex}")
                # Устанавливаем pending для повторной попытки через beat
                Video.objects.filter(pk=video_id).update(processing_status="pending")
        
        thread = threading.Thread(target=delayed_task, daemon=True)
        thread.start()
        logger.info(f"[SIGNAL] Started background thread for video {video_id}")
        return
    except Exception as e:
        logger.error(f"[SIGNAL] All methods failed for video {video_id}: {e}")
    
    # Если всё упало - ставим pending, Celery Beat подхватит через process_pending_videos
    Video.objects.filter(pk=video_id).update(processing_status="pending")
    logger.warning(f"[SIGNAL] Video {video_id} set to pending for later processing")


@receiver(pre_delete, sender=Video)
def video_pre_delete(sender, instance, **kwargs):
    """Удаление файлов при удалении видео."""
    import os
    from django.conf import settings
    
    # Обновляем счётчик видео
    if instance.created_by and instance.created_by.videos_count > 0:
        try:
            instance.created_by.videos_count -= 1
            instance.created_by.save(update_fields=["videos_count"])
        except Exception:
            pass

    # Удаляем файлы
    try:
        if instance.temp_video_file:
            instance.temp_video_file.delete(save=False)
        if instance.preview:
            instance.preview.delete(save=False)
        if instance.poster:
            instance.poster.delete(save=False)
        
        # Удаляем сконвертированные файлы
        if instance.converted_files:
            for file_path in instance.converted_files:
                full_path = os.path.join(settings.MEDIA_ROOT, file_path)
                try:
                    if os.path.exists(full_path):
                        os.remove(full_path)
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Error deleting files for video {instance.id}: {e}")
