"""
Models for the models app.
"""
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()
import transliterate
from django.utils.text import slugify


class Model(models.Model):
    """Model for adult performers."""

    # Basic info
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="model_profile"
    )
    slug = models.SlugField(max_length=200, blank=True, null=True, unique=True)

    # Display info
    display_name = models.CharField(
        max_length=100, help_text="Stage name or display name"
    )
    bio = models.TextField(blank=True, help_text="Biography")
    avatar = models.ImageField(upload_to="models/avatars/", blank=True, null=True)
    cover_photo = models.ImageField(upload_to="models/covers/", blank=True, null=True)

    # Personal info
    GENDER_CHOICES = [
        ("female", "Женщина"),
        ("male", "Мужчина"),
        ("trans", "Трансгендер"),
        ("other", "Другое"),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default="female")
    age = models.PositiveIntegerField(blank=True, null=True, help_text="Age in years")
    birth_date = models.DateField(blank=True, null=True)
    country = models.CharField(
        max_length=100, blank=True, help_text="Country of origin"
    )
    ethnicity = models.CharField(max_length=100, blank=True, help_text="Ethnicity")

    # Career info
    career_start = models.DateField(
        blank=True, null=True, help_text="Career start date"
    )
    zodiac_sign = models.CharField(max_length=20, blank=True, help_text="Zodiac sign")

    # Physical characteristics
    HAIR_COLOR_CHOICES = [
        ("blonde", "Блондинка"),
        ("brunette", "Брюнетка"),
        ("redhead", "Рыжая"),
        ("black", "Черная"),
        ("brown", "Коричневая"),
        ("gray", "Серая"),
        ("other", "Другое"),
    ]
    hair_color = models.CharField(max_length=20, choices=HAIR_COLOR_CHOICES, blank=True)

    EYE_COLOR_CHOICES = [
        ("blue", "Голубые"),
        ("brown", "Коричневые"),
        ("green", "Зеленые"),
        ("hazel", "Ореховые"),
        ("gray", "Серые"),
        ("other", "Другое"),
    ]
    eye_color = models.CharField(max_length=20, choices=EYE_COLOR_CHOICES, blank=True)

    # Body characteristics
    has_tattoos = models.BooleanField(default=False)
    tattoos_description = models.TextField(
        blank=True, help_text="Description of tattoos"
    )
    has_piercings = models.BooleanField(default=False)
    piercings_description = models.TextField(
        blank=True, help_text="Description of piercings"
    )

    # Measurements
    BREAST_SIZE_CHOICES = [
        ("small", "Маленькая"),
        ("medium", "Средняя"),
        ("large", "Большая"),
        ("very_large", "Очень большая"),
    ]
    breast_size = models.CharField(
        max_length=20, choices=BREAST_SIZE_CHOICES, blank=True
    )
    measurements = models.CharField(
        max_length=50, blank=True, help_text="Body measurements (e.g., 32A-60-83)"
    )
    height = models.PositiveIntegerField(
        blank=True, null=True, help_text="Height in cm"
    )
    weight = models.PositiveIntegerField(
        blank=True, null=True, help_text="Weight in kg"
    )

    # Statistics
    views_count = models.PositiveIntegerField(default=0)
    subscribers_count = models.PositiveIntegerField(default=0)
    videos_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)

    # Status
    is_verified = models.BooleanField(default=False, help_text="Verified model")
    is_active = models.BooleanField(default=True)
    is_premium = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Model"
        verbose_name_plural = "Models"
        ordering = ["-created_at"]

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        if not self.slug:
            # Try to transliterate cyrillic to latin first
            try:
                transliterated_name = transliterate.translit(
                    self.display_name, "ru", reversed=True
                )
                base_slug = slugify(transliterated_name)
            except:
                # Fallback to regular slugify
                base_slug = slugify(self.display_name)

            # If slug is still empty, use model ID
            if not base_slug:
                base_slug = f"model-{self.id}" if self.id else "model"

            self.slug = base_slug
            counter = 1
            while Model.objects.filter(slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)

    @property
    def age_display(self):
        """Display age with proper formatting."""
        if self.age:
            return f"{self.age} лет"
        return "Не указан"

    @property
    def height_display(self):
        """Display height with proper formatting."""
        if self.height:
            feet = self.height // 30.48  # Convert cm to feet
            inches = (self.height % 30.48) / 2.54  # Convert remaining cm to inches
            return f"{self.height} см ({int(feet)} ft {int(inches)} inch)"
        return "Не указан"

    @property
    def weight_display(self):
        """Display weight with proper formatting."""
        if self.weight:
            lbs = self.weight * 2.20462  # Convert kg to lbs
            return f"{self.weight} кг ({int(lbs)} lb)"
        return "Не указан"


class ModelVideo(models.Model):
    """Many-to-many relationship between models and videos."""

    model = models.ForeignKey(
        Model, on_delete=models.CASCADE, related_name="model_videos"
    )
    video = models.ForeignKey(
        "videos.Video", on_delete=models.CASCADE, related_name="video_models"
    )
    is_primary = models.BooleanField(
        default=False, help_text="Primary model in this video"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Model Video"
        verbose_name_plural = "Model Videos"
        unique_together = ["model", "video"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.model.display_name} in {self.video.title}"


class ModelSubscription(models.Model):
    """Model for user subscriptions to models."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="model_subscriptions"
    )
    model = models.ForeignKey(
        Model, on_delete=models.CASCADE, related_name="subscribers"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Model Subscription"
        verbose_name_plural = "Model Subscriptions"
        unique_together = ["user", "model"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} subscribed to {self.model.display_name}"


class ModelLike(models.Model):
    """Model for user likes on models."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="model_likes")
    model = models.ForeignKey(Model, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Model Like"
        verbose_name_plural = "Model Likes"
        unique_together = ["user", "model"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} likes {self.model.display_name}"
