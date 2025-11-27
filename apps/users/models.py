"""
User models for TubeCMS.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .managers import NotificationManager, SubscriptionManager, UserManager

# Choices
GENDER_CHOICES = [
    ("male", "Male"),
    ("female", "Female"),
    ("other", "Other"),
    ("prefer_not_to_say", "Prefer not to say"),
]

ORIENTATION_CHOICES = [
    ("straight", "Straight"),
    ("gay", "Gay"),
    ("lesbian", "Lesbian"),
    ("bisexual", "Bisexual"),
    ("pansexual", "Pansexual"),
    ("other", "Other"),
    ("prefer_not_to_say", "Prefer not to say"),
]

MARITAL_STATUS_CHOICES = [
    ("single", "Single"),
    ("married", "Married"),
    ("divorced", "Divorced"),
    ("widowed", "Widowed"),
    ("separated", "Separated"),
    ("in_relationship", "In a relationship"),
    ("prefer_not_to_say", "Prefer not to say"),
]

COUNTRY_CHOICES = [
    ("US", "United States"),
    ("GB", "United Kingdom"),
    ("CA", "Canada"),
    ("AU", "Australia"),
    ("DE", "Germany"),
    ("FR", "France"),
    ("IT", "Italy"),
    ("ES", "Spain"),
    ("NL", "Netherlands"),
    ("SE", "Sweden"),
    ("NO", "Norway"),
    ("DK", "Denmark"),
    ("FI", "Finland"),
    ("PL", "Poland"),
    ("CZ", "Czech Republic"),
    ("RU", "Russia"),
    ("UA", "Ukraine"),
    ("BY", "Belarus"),
    ("KZ", "Kazakhstan"),
    ("JP", "Japan"),
    ("KR", "South Korea"),
    ("CN", "China"),
    ("IN", "India"),
    ("BR", "Brazil"),
    ("MX", "Mexico"),
    ("AR", "Argentina"),
    ("other", "Other"),
]

LANGUAGE_CHOICES = [
    ("en", "English"),
    ("ru", "Русский"),
]

THEME_CHOICES = [
    ("light", "Light"),
    ("dark", "Dark"),
]

PRIVACY_CHOICES = [
    ("public", "Public"),
    ("private", "Private"),
]


class User(AbstractUser):
    """Custom user model with additional fields."""

    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True, verbose_name="Обо мне")
    birth_date = models.DateField(blank=True, null=True, verbose_name="Дата рождения")
    location = models.CharField(max_length=100, blank=True, verbose_name="Город")
    country = models.CharField(
        max_length=50, choices=COUNTRY_CHOICES, blank=True, verbose_name="Страна"
    )
    gender = models.CharField(
        max_length=20, choices=GENDER_CHOICES, blank=True, verbose_name="Пол"
    )
    orientation = models.CharField(
        max_length=20,
        choices=ORIENTATION_CHOICES,
        blank=True,
        verbose_name="Сексуальная ориентация",
    )
    marital_status = models.CharField(
        max_length=20,
        choices=MARITAL_STATUS_CHOICES,
        blank=True,
        verbose_name="Семейное положение",
    )
    education = models.CharField(max_length=200, blank=True, verbose_name="Образование")
    website = models.URLField(blank=True, verbose_name="Веб-сайт")
    is_verified = models.BooleanField(default=False)
    subscribers_count = models.PositiveIntegerField(default=0)
    videos_count = models.PositiveIntegerField(default=0)
    total_views = models.PositiveIntegerField(default=0)
    
    # Priority system for video processing
    is_premium = models.BooleanField(
        default=False,
        verbose_name="Premium пользователь",
        help_text="Premium пользователи получают приоритет в обработке видео"
    )
    processing_priority = models.IntegerField(
        default=5,
        verbose_name="Приоритет обработки",
        help_text="Чем выше число, тем выше приоритет (0-10)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    # Managers
    objects = UserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username

    @property
    def full_name(self):
        """Return user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    @property
    def display_name(self):
        """Return display name for the user."""
        return self.full_name or self.username

    @property
    def model_profile(self):
        """Return model profile if exists."""
        try:
            return self.model
        except:
            return None

    @property
    def age(self):
        """Calculate user's age from birth_date."""
        if self.birth_date:
            today = timezone.now().date()
            return (
                today.year
                - self.birth_date.year
                - (
                    (today.month, today.day)
                    < (self.birth_date.month, self.birth_date.day)
                )
            )
        return None
    
    def get_processing_priority(self):
        """
        Get processing priority for video tasks.
        
        Priority levels:
        - 10: Premium users with high priority
        - 7-9: Premium users
        - 5: Regular users (default)
        - 3: New users (< 5 videos)
        - 1: Users with many failed videos
        
        Returns:
            int: Priority level (0-10)
        """
        if self.is_premium:
            return max(7, self.processing_priority)
        
        # Boost priority for active users
        if self.videos_count > 50:
            return min(6, self.processing_priority + 1)
        
        # Lower priority for new users
        if self.videos_count < 5:
            return 3
        
        return self.processing_priority

    def get_gender_display_ru(self):
        """Return gender in Russian."""
        gender_ru = {
            "male": "Мужской",
            "female": "Женский",
            "other": "Другой",
            "prefer_not_to_say": "Предпочитаю не указывать",
        }
        return gender_ru.get(self.gender, "")

    def get_orientation_display_ru(self):
        """Return orientation in Russian."""
        orientation_ru = {
            "straight": "Гетеросексуал",
            "gay": "Гей",
            "lesbian": "Лесбиянка",
            "bisexual": "Бисексуал",
            "pansexual": "Пансексуал",
            "other": "Другая",
            "prefer_not_to_say": "Предпочитаю не указывать",
        }
        return orientation_ru.get(self.orientation, "")


class Subscription(models.Model):
    """User subscriptions."""

    subscriber = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="subscriptions"
    )
    channel = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="subscribers"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Managers
    objects = SubscriptionManager()

    class Meta:
        unique_together = ["subscriber", "channel"]
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"

    def __str__(self):
        return f"{self.subscriber} subscribes to {self.channel}"


class UserProfile(models.Model):
    """Extended user profile."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    theme_preference = models.CharField(
        max_length=10, choices=THEME_CHOICES, default="dark"
    )
    language = models.CharField(
        max_length=5, choices=LANGUAGE_CHOICES, default="en", verbose_name="Язык"
    )
    notifications_enabled = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    privacy_level = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default="public",
    )

    # Privacy settings for profile sections
    show_videos_publicly = models.BooleanField(
        default=True, verbose_name="Show videos publicly"
    )
    show_favorites_publicly = models.BooleanField(
        default=False, verbose_name="Show favorites publicly"
    )
    show_watch_later_publicly = models.BooleanField(
        default=False, verbose_name="Show watch later publicly"
    )
    show_friends_publicly = models.BooleanField(
        default=True, verbose_name="Show friends publicly"
    )

    # Additional profile fields
    country = models.CharField(max_length=100, blank=True, verbose_name="Страна")

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username}'s profile"


class Friendship(models.Model):
    """Система дружбы между пользователями."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("blocked", "Blocked"),
    ]

    from_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_friend_requests"
    )
    to_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="received_friend_requests"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["from_user", "to_user"]
        verbose_name = "Friendship"
        verbose_name_plural = "Friendships"

    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.status})"

    @classmethod
    def get_friends(cls, user):
        """Получить список друзей пользователя."""
        friend_ids = cls.objects.filter(
            models.Q(from_user=user, status="accepted")
            | models.Q(to_user=user, status="accepted")
        ).values_list("from_user_id", "to_user_id")

        all_friend_ids = set()
        for from_id, to_id in friend_ids:
            if from_id == user.id:
                all_friend_ids.add(to_id)
            else:
                all_friend_ids.add(from_id)

        return User.objects.filter(id__in=all_friend_ids).select_related("profile")

    @classmethod
    def get_friendship_status(cls, user1, user2):
        """Получить статус дружбы между двумя пользователями."""
        try:
            friendship = cls.objects.get(
                models.Q(from_user=user1, to_user=user2)
                | models.Q(from_user=user2, to_user=user1)
            )
            return friendship.status, friendship
        except cls.DoesNotExist:
            return None, None

    @classmethod
    def are_friends(cls, user1, user2):
        """Проверить, являются ли пользователи друзьями."""
        status, _ = cls.get_friendship_status(user1, user2)
        return status == "accepted"


class Notification(models.Model):
    """Система уведомлений."""

    TYPE_CHOICES = [
        ("friend_request", "Friend Request"),
        ("friend_accepted", "Friend Request Accepted"),
        ("new_subscriber", "New Subscriber"),
        ("new_video", "New Video from Friend/Subscription"),
        ("video_like", "Video Liked"),
        ("video_comment", "New Comment"),
        ("system", "System Notification"),
    ]

    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_notifications",
        null=True,
        blank=True,
    )
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Дополнительные поля для связи с объектами
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object_type = models.CharField(max_length=50, null=True, blank=True)
    action_url = models.URLField(null=True, blank=True)

    # Managers
    objects = NotificationManager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.recipient.username}: {self.title}"

    def mark_as_read(self):
        """Отметить уведомление как прочитанное."""
        self.is_read = True
        self.save(update_fields=["is_read"])

    @classmethod
    def create_friend_request_notification(cls, from_user, to_user):
        """Создать уведомление о запросе дружбы."""
        return cls.objects.create(
            recipient=to_user,
            sender=from_user,
            notification_type="friend_request",
            title="Новый запрос в друзья",
            message=f"{from_user.username} хочет добавить вас в друзья",
            action_url=f"/members/{from_user.username}/",
        )

    @classmethod
    def create_friend_accepted_notification(cls, from_user, to_user):
        """Создать уведомление о принятии дружбы."""
        return cls.objects.create(
            recipient=from_user,
            sender=to_user,
            notification_type="friend_accepted",
            title="Запрос в друзья принят",
            message=f"{to_user.username} принял ваш запрос в друзья",
            action_url=f"/members/{to_user.username}/",
        )

    @classmethod
    def create_new_subscriber_notification(cls, subscriber, channel):
        """Создать уведомление о новом подписчике."""
        return cls.objects.create(
            recipient=channel,
            sender=subscriber,
            notification_type="new_subscriber",
            title="Новый подписчик",
            message=f"{subscriber.username} подписался на ваш канал",
            action_url=f"/members/{subscriber.username}/",
        )

    @classmethod
    def create_new_video_notification(cls, video_owner, follower):
        """Создать уведомление о новом видео от друга/подписки."""
        return cls.objects.create(
            recipient=follower,
            sender=video_owner,
            notification_type="new_video",
            title="Новое видео",
            message=f"{video_owner.username} добавил новое видео",
            action_url=f"/videos/{video_owner.created_videos.last().slug}/"
            if video_owner.created_videos.exists()
            else f"/members/{video_owner.username}/",
        )
