from django.core.management.base import BaseCommand

from apps.core.models import Category


class Command(BaseCommand):
    help = "Update icon for Blowjob category"

    def handle(self, *args, **options):
        try:
            category = Category.objects.get(name="Blowjob")
            category.icon = "lips"
            category.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully updated icon for category: {category.name}"
                )
            )
        except Category.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Category "Blowjob" not found. Create it first.')
            )
