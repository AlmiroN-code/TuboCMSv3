"""
Signals for video model.
"""
from django.conf import settings
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from .models import Video
from .tasks import cleanup_old_videos, process_video_async

# Сохраняем старое значение файла перед сохранением
_old_temp_video_file = {}


@receiver(pre_save, sender=Video)
def video_pre_save(sender, instance, **kwargs):
    """Сохраняем старое значение temp_video_file перед сохранением."""
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            old_file = (
                old_instance.temp_video_file.name
                if old_instance.temp_video_file
                else None
            )
            _old_temp_video_file[instance.pk] = old_file
            print(
                f"[SIGNAL PRE_SAVE] Video {instance.pk}: old_file={old_file}, new_file={instance.temp_video_file.name if instance.temp_video_file else None}"
            )
        except sender.DoesNotExist:
            _old_temp_video_file[instance.pk] = None
            print(f"[SIGNAL PRE_SAVE] Video {instance.pk}: new object (no old file)")
    else:
        # Для нового объекта используем временный ID
        temp_id = id(instance)
        new_file = instance.temp_video_file.name if instance.temp_video_file else None
        _old_temp_video_file[temp_id] = None
        instance._temp_signal_id = temp_id
        print(
            f"[SIGNAL PRE_SAVE] New video (temp_id={temp_id}): no old file, new_file={new_file}"
        )


@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    """Handle video post-save events - запускать обработку всегда, если есть temp_video_file и он изменился."""
    # Получаем старое значение файла из сохраненного перед save
    old_file = None
    if instance.pk:
        old_file = _old_temp_video_file.pop(instance.pk, None)
    elif hasattr(instance, "_temp_signal_id"):
        temp_id = instance._temp_signal_id
        old_file = _old_temp_video_file.pop(temp_id, None)

    # Получаем новое значение файла
    new_file = instance.temp_video_file.name if instance.temp_video_file else None

    # Проверяем, существует ли файл физически
    file_exists = False
    if instance.temp_video_file:
        try:
            file_exists = instance.temp_video_file.storage.exists(
                instance.temp_video_file.name
            )
        except:
            try:
                import os

                file_exists = os.path.exists(instance.temp_video_file.path)
            except:
                file_exists = False

    print(
        f"[SIGNAL POST_SAVE] Video {instance.id}: created={created}, old_file={old_file}, new_file={new_file}, file_exists={file_exists}, processing_status={instance.processing_status}"
    )

    # Запускать обработку, если:
    # 1. Видео создано и есть файл, который существует физически
    # 2. Файл появился (было None, стало есть) и файл существует
    # 3. Файл изменился (старый файл != новый файл) и новый файл существует
    # 4. Файл существует, но обработка еще не запускалась (processing_status = 'pending')
    should_process = False
    if created and new_file and file_exists:
        should_process = True
        print(f"[SIGNAL] [OK] NEW video {instance.id} with file: {new_file}")
    elif new_file and file_exists and (not old_file or old_file != new_file):
        should_process = True
        print(
            f"[SIGNAL] [OK] Video {instance.id} file changed: {old_file} -> {new_file}"
        )
    elif new_file and file_exists and instance.processing_status == "pending":
        # Если файл есть, но обработка еще не запускалась
        should_process = True
        print(
            f"[SIGNAL] [OK] Video {instance.id} has file but processing not started yet: {new_file}"
        )
    else:
        print(
            f"[SIGNAL] [SKIP] Skipping processing for video {instance.id}: created={created}, old_file={old_file}, new_file={new_file}, file_exists={file_exists}, processing_status={instance.processing_status}"
        )

    if should_process:
        # Проверяем, не обрабатывается ли уже видео
        if instance.processing_status in ["processing", "completed"]:
            print(
                f"(Signal) [SKIP] Video {instance.id} is already processing or completed. Status: {instance.processing_status}"
            )
            return

        selected_profiles = getattr(instance, "_selected_encoding_profiles", None)
        print(
            f"[SIGNAL] [START] Starting async processing for video {instance.id} (created={created}, profiles={selected_profiles})"
        )

        # Устанавливаем статус processing БЕЗ вызова сигналов
        Video.objects.filter(pk=instance.pk).update(processing_status="processing")
        instance.processing_status = "processing"  # Обновляем локальный объект
        print(f"[SIGNAL] [STATUS] Video {instance.id} status set to 'processing'")

        # Запускаем обработку в фоновом потоке, чтобы не блокировать сохранение
        # Это работает как с Celery eager режимом, так и с реальным Celery worker
        import threading
        
        def run_processing():
            """Запуск обработки в отдельном потоке."""
            import django
            django.db.connections.close_all()  # Закрываем соединения для нового потока
            
            try:
                from apps.videos.tasks import process_video_async
                from apps.videos.priority_utils import PriorityManager
                
                # Определяем приоритет на основе пользователя и видео
                priority = PriorityManager.get_priority_for_video(instance)
                priority_label = PriorityManager.get_priority_label(priority)
                
                if instance.created_by:
                    print(f"[SIGNAL] [PRIORITY] User {instance.created_by.username} (premium={instance.created_by.is_premium}): priority={priority} ({priority_label})")
                else:
                    print(f"[SIGNAL] [PRIORITY] No user: priority={priority} ({priority_label})")
                
                # Запускаем задачу с приоритетом
                result = process_video_async.apply_async(
                    args=[instance.id, selected_profiles],
                    priority=priority,
                    queue='video_processing'
                )
                print(
                    f"[SIGNAL] [SUCCESS] Processing task queued for video {instance.id} with priority {priority} ({priority_label})"
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to process video {instance.id}: {e}")
                # Устанавливаем статус в 'pending' для ручной обработки позже
                try:
                    Video.objects.filter(pk=instance.pk).update(processing_status="pending")
                except:
                    pass
        
        # Запускаем в фоновом потоке
        thread = threading.Thread(target=run_processing, daemon=True)
        thread.start()
        print(f"[SIGNAL] [ASYNC] Background processing started for video {instance.id}")

    # Обновление счётчика видео
    if created and instance.created_by:
        instance.created_by.videos_count += 1
        instance.created_by.save(update_fields=["videos_count"])

    # Slug is handled in the model's save method


@receiver(pre_delete, sender=Video)
def video_pre_delete(sender, instance, **kwargs):
    """Handle video pre-delete events."""
    # Update user's video count
    if instance.created_by and instance.created_by.videos_count > 0:
        instance.created_by.videos_count -= 1
        instance.created_by.save(update_fields=["videos_count"])

    # Delete associated files
    try:
        if instance.temp_video_file:
            instance.temp_video_file.delete(save=False)
        if instance.preview:
            instance.preview.delete(save=False)
        if instance.poster:
            instance.poster.delete(save=False)
        # Delete converted files
        if instance.converted_files:
            import os

            from django.conf import settings

            for file_path in instance.converted_files:
                full_path = os.path.join(settings.MEDIA_ROOT, file_path)
                try:
                    if os.path.exists(full_path):
                        os.remove(full_path)
                except Exception as e:
                    print(f"Error deleting converted file {full_path}: {e}")
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(
            f"Error deleting video files for video {instance.id}: {e}", exc_info=True
        )


# Periodic tasks
from celery import shared_task


@shared_task
def periodic_cleanup():
    """Periodic cleanup task."""
    cleanup_old_videos.delay()
