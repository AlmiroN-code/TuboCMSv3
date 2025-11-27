"""
Tests for Video models and related functionality.
"""

import pytest

from apps.core.models import Category
from apps.users.models import User

from .models import Rating, Video, VideoLike, WatchLater


@pytest.fixture
def test_user():
    """Create a test user."""
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )


@pytest.fixture
def test_category():
    """Create a test category."""
    return Category.objects.create(name="Test Category", slug="test-category")


@pytest.fixture
def test_video(test_user, test_category):
    """Create a test video."""
    video = Video.objects.create(
        created_by=test_user,
        title="Test Video",
        description="This is a test video",
        category=test_category,
        duration=120,
        resolution="1920x1080",
        format="mp4",
        status="published",
    )
    return video


@pytest.mark.django_db
class TestVideoModel:
    """Test Video model functionality."""

    def test_video_creation(self, test_video):
        """Test basic video creation."""
        assert test_video.title == "Test Video"
        assert test_video.status == "published"
        assert test_video.created_by.username == "testuser"
        assert test_video.category.name == "Test Category"

    def test_video_slug_generation(self, test_user):
        """Test automatic slug generation."""
        video = Video.objects.create(
            created_by=test_user, title="Тестовое видео с русским", status="draft"
        )
        assert video.slug == "testovoe-video-s-russkim"
        video.delete()

    def test_video_slug_uniqueness(self, test_user):
        """Test slug uniqueness handling."""
        video1 = Video.objects.create(
            created_by=test_user, title="Same Title", status="draft"
        )
        video2 = Video.objects.create(
            created_by=test_user, title="Same Title", status="draft"
        )
        assert video1.slug == "same-title"
        assert video2.slug == "same-title-1"
        video1.delete()
        video2.delete()

    def test_duration_formatted(self, test_video):
        """Test duration formatting."""
        assert test_video.duration_formatted == "02:00"

        test_video.duration = 3661  # 1h 1m 1s
        test_video.save()
        assert test_video.duration_formatted == "01:01:01"

    def test_primary_video_file_property(self, test_video):
        """Test primary_video_file property."""
        # Should return None if no files
        assert test_video.primary_video_file is None

    def test_increment_views(self, test_video):
        """Test view increment functionality."""
        initial_views = test_video.views_count
        test_video.increment_views()
        test_video.refresh_from_db()
        assert test_video.views_count == initial_views + 1

    def test_user_property(self, test_video):
        """Test backward compatibility user property."""
        assert test_video.user == test_video.created_by


@pytest.mark.django_db
class TestVideoLike:
    """Test VideoLike model."""

    def test_like_creation(self, test_user, test_video):
        """Test creating likes."""
        like = VideoLike.objects.create(user=test_user, video=test_video, value=1)
        assert like.value == 1
        assert like.user == test_user
        assert like.video == test_video

    def test_unique_constraint(self, test_user, test_video):
        """Test unique constraint for user-video likes."""
        VideoLike.objects.create(user=test_user, video=test_video, value=1)

        with pytest.raises(Exception):  # Should raise IntegrityError
            VideoLike.objects.create(user=test_user, video=test_video, value=-1)


@pytest.mark.django_db
class TestRating:
    """Test Rating model."""

    def test_rating_creation(self, test_video):
        """Test creating ratings."""
        # Rating with IP only
        rating = Rating.objects.create(
            video=test_video, ip_address="127.0.0.1", value=-1
        )
        assert rating.value == -1
        assert rating.ip_address == "127.0.0.1"

    def test_rating_validation(self, test_video, test_user):
        """Test rating validation."""
        # Should require either user or ip_address
        with pytest.raises(ValueError):
            Rating.objects.create(video=test_video, value=1)

        # Should not allow both
        with pytest.raises(ValueError):
            Rating.objects.create(
                video=test_video, user=test_user, ip_address="127.0.0.1", value=1
            )


@pytest.mark.django_db
class TestWatchLater:
    """Test WatchLater model."""

    def test_watch_later_creation(self, test_user, test_video):
        """Test creating watch later entries."""
        watch = WatchLater.objects.create(user=test_user, video=test_video)
        assert watch.user == test_user
        assert watch.video == test_video

    def test_unique_constraint_watch_later(self, test_user, test_video):
        """Test unique constraint for watch later."""
        WatchLater.objects.create(user=test_user, video=test_video)

        with pytest.raises(Exception):
            WatchLater.objects.create(user=test_user, video=test_video)
