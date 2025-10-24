from django.core.management.base import BaseCommand
from apps.core.models import Category
from django.utils.text import slugify


class Command(BaseCommand):
    help = 'Add new video categories'

    def handle(self, *args, **options):
        categories_data = [
            {
                'name': 'Amateur',
                'description': 'Amateur videos',
                'icon': 'fas fa-user',
                'order': 1
            },
            {
                'name': 'Anal',
                'description': 'Anal videos',
                'icon': 'fas fa-circle',
                'order': 2
            },
            {
                'name': 'Big Ass',
                'description': 'Big ass videos',
                'icon': 'fas fa-heart',
                'order': 3
            },
            {
                'name': 'Big Dick',
                'description': 'Big dick videos',
                'icon': 'fas fa-male',
                'order': 4
            },
            {
                'name': 'Big Tits',
                'description': 'Big tits videos',
                'icon': 'fas fa-female',
                'order': 5
            },
            {
                'name': 'Blacks',
                'description': 'Black performers videos',
                'icon': 'fas fa-users',
                'order': 6
            },
            {
                'name': 'Blonde',
                'description': 'Blonde performers videos',
                'icon': 'fas fa-star',
                'order': 7
            },
            {
                'name': 'Blowjob',
                'description': 'Blowjob videos',
                'icon': 'fas fa-lips',
                'order': 8
            },
            {
                'name': 'Brunette',
                'description': 'Brunette performers videos',
                'icon': 'fas fa-star-half-alt',
                'order': 9
            },
            {
                'name': 'Car',
                'description': 'Car videos',
                'icon': 'fas fa-car',
                'order': 10
            },
            {
                'name': 'Cumshot',
                'description': 'Cumshot videos',
                'icon': 'fas fa-tint',
                'order': 11
            },
            {
                'name': 'Doggy style',
                'description': 'Doggy style videos',
                'icon': 'fas fa-paw',
                'order': 12
            },
            {
                'name': 'Hardcore',
                'description': 'Hardcore videos',
                'icon': 'fas fa-fire',
                'order': 13
            },
            {
                'name': 'Lesbian',
                'description': 'Lesbian videos',
                'icon': 'fas fa-venus-double',
                'order': 14
            },
            {
                'name': 'Masturbation',
                'description': 'Masturbation videos',
                'icon': 'fas fa-hand-paper',
                'order': 15
            },
            {
                'name': 'Milf',
                'description': 'MILF videos',
                'icon': 'fas fa-crown',
                'order': 16
            }
        ]

        created_count = 0
        updated_count = 0

        for category_data in categories_data:
            slug = slugify(category_data['name'])
            
            category, created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': category_data['name'],
                    'description': category_data['description'],
                    'icon': category_data['icon'],
                    'order': category_data['order'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created category: {category.name}')
                )
            else:
                # Update existing category
                category.name = category_data['name']
                category.description = category_data['description']
                category.icon = category_data['icon']
                category.order = category_data['order']
                category.is_active = True
                category.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated category: {category.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {len(categories_data)} categories. '
                f'Created: {created_count}, Updated: {updated_count}'
            )
        )
