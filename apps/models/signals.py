"""
Signals for models app.
"""
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import Model, ModelLike, ModelSubscription, ModelVideo

User = get_user_model()


@receiver(post_save, sender=Model)
def model_post_save(sender, instance, created, **kwargs):
    """Handle model post-save events."""
    pass


@receiver(pre_delete, sender=Model)
def model_pre_delete(sender, instance, **kwargs):
    """Handle model pre-delete events."""
    pass


@receiver(post_save, sender=ModelVideo)
def model_video_post_save(sender, instance, created, **kwargs):
    """Handle model video post-save events."""
    if created:
        # Update model's video count
        instance.model.videos_count += 1
        instance.model.save(update_fields=["videos_count"])


@receiver(pre_delete, sender=ModelVideo)
def model_video_pre_delete(sender, instance, **kwargs):
    """Handle model video pre-delete events."""
    # Update model's video count
    if instance.model.videos_count > 0:
        instance.model.videos_count -= 1
        instance.model.save(update_fields=["videos_count"])


@receiver(post_save, sender=ModelSubscription)
def model_subscription_post_save(sender, instance, created, **kwargs):
    """Handle model subscription post-save events."""
    if created:
        # Update model's subscriber count
        instance.model.subscribers_count += 1
        instance.model.save(update_fields=["subscribers_count"])


@receiver(pre_delete, sender=ModelSubscription)
def model_subscription_pre_delete(sender, instance, **kwargs):
    """Handle model subscription pre-delete events."""
    # Update model's subscriber count
    if instance.model.subscribers_count > 0:
        instance.model.subscribers_count -= 1
        instance.model.save(update_fields=["subscribers_count"])


@receiver(post_save, sender=ModelLike)
def model_like_post_save(sender, instance, created, **kwargs):
    """Handle model like post-save events."""
    if created:
        # Update model's like count
        instance.model.likes_count += 1
        instance.model.save(update_fields=["likes_count"])


@receiver(pre_delete, sender=ModelLike)
def model_like_pre_delete(sender, instance, **kwargs):
    """Handle model like pre-delete events."""
    # Update model's like count
    if instance.model.likes_count > 0:
        instance.model.likes_count -= 1
        instance.model.save(update_fields=["likes_count"])
