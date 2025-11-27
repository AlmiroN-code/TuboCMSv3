"""
Management command to create initial site settings.
"""
from django.core.management.base import BaseCommand

from apps.core.models import SEOSettings, SiteSettings


class Command(BaseCommand):
    help = "Create initial site settings"

    def handle(self, *args, **options):
        # Create default site settings if none exist
        if not SiteSettings.objects.filter(is_active=True).exists():
            SiteSettings.objects.create(
                site_name="TubeCMS",
                add_site_name_to_title=True,
                allow_registration=True,
                auto_publish_videos=False,
                require_moderation=True,
                max_video_size=500,
                max_video_duration=3600,
                allowed_video_formats="mp4,avi,mov,wmv",
                is_active=True,
            )
            self.stdout.write(
                self.style.SUCCESS("Successfully created default site settings")
            )
        else:
            self.stdout.write(self.style.WARNING("Site settings already exist"))

        # Create default SEO settings if none exist
        if not SEOSettings.objects.filter(is_active=True).exists():
            SEOSettings.objects.create(
                meta_title="TubeCMS - Видео хостинг",
                meta_description="Современный видео-хостинг на Django и HTMX. Загружайте, смотрите и делитесь видео.",
                meta_keywords="видео, хостинг, django, htmx, загрузка видео",
                og_title="TubeCMS - Видео хостинг",
                og_description="Современный видео-хостинг на Django и HTMX",
                twitter_card="summary_large_image",
                sitemap_enabled=True,
                is_active=True,
            )
            self.stdout.write(
                self.style.SUCCESS("Successfully created default SEO settings")
            )
        else:
            self.stdout.write(self.style.WARNING("SEO settings already exist"))
