"""
Management command to create test models.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.models.models import Model

User = get_user_model()


class Command(BaseCommand):
    help = "Create test models for development"

    def handle(self, *args, **options):
        # Create test users and models
        test_models = [
            {
                "username": "angel_emily",
                "email": "angel.emily@example.com",
                "display_name": "Angel Emily",
                "bio": "Professional adult performer from France. Started my career in 2017 and love creating content for my fans.",
                "gender": "female",
                "age": 28,
                "country": "France",
                "ethnicity": "Белая (Белый)",
                "hair_color": "blonde",
                "eye_color": "blue",
                "has_tattoos": True,
                "tattoos_description": "Right thigh (flower with ornament), left body side (cardiogram), inside left forearm (bouddhisme elephant), right side of abdomen (five paw print)",
                "has_piercings": True,
                "piercings_description": "Multiple piercings",
                "breast_size": "small",
                "measurements": "32A-60-83",
                "height": 154,
                "weight": 46,
                "zodiac_sign": "Pisces",
                "views_count": 82000,
                "subscribers_count": 240,
                "videos_count": 168,
                "likes_count": 186,
                "is_verified": True,
            },
            {
                "username": "sophia_rose",
                "email": "sophia.rose@example.com",
                "display_name": "Sophia Rose",
                "bio": "Curvy brunette from Italy. Passionate about creating intimate content and connecting with my audience.",
                "gender": "female",
                "age": 25,
                "country": "Italy",
                "ethnicity": "Белая (Белый)",
                "hair_color": "brunette",
                "eye_color": "brown",
                "has_tattoos": False,
                "has_piercings": True,
                "piercings_description": "Ear piercings",
                "breast_size": "large",
                "measurements": "36D-65-90",
                "height": 168,
                "weight": 58,
                "zodiac_sign": "Leo",
                "views_count": 45000,
                "subscribers_count": 180,
                "videos_count": 95,
                "likes_count": 120,
                "is_verified": True,
            },
            {
                "username": "luna_moon",
                "email": "luna.moon@example.com",
                "display_name": "Luna Moon",
                "bio": "Alternative model with unique style. Love expressing myself through art and adult content.",
                "gender": "female",
                "age": 22,
                "country": "Germany",
                "ethnicity": "Белая (Белый)",
                "hair_color": "black",
                "eye_color": "green",
                "has_tattoos": True,
                "tattoos_description": "Full sleeve on left arm, back piece",
                "has_piercings": True,
                "piercings_description": "Multiple facial and body piercings",
                "breast_size": "medium",
                "measurements": "34C-62-85",
                "height": 165,
                "weight": 52,
                "zodiac_sign": "Scorpio",
                "views_count": 32000,
                "subscribers_count": 150,
                "videos_count": 75,
                "likes_count": 95,
                "is_verified": False,
            },
            {
                "username": "ruby_red",
                "email": "ruby.red@example.com",
                "display_name": "Ruby Red",
                "bio": "Fiery redhead from Ireland. Passionate performer who loves to entertain and please my fans.",
                "gender": "female",
                "age": 26,
                "country": "Ireland",
                "ethnicity": "Белая (Белый)",
                "hair_color": "redhead",
                "eye_color": "green",
                "has_tattoos": False,
                "has_piercings": False,
                "breast_size": "medium",
                "measurements": "34B-64-88",
                "height": 170,
                "weight": 55,
                "zodiac_sign": "Aries",
                "views_count": 28000,
                "subscribers_count": 120,
                "videos_count": 60,
                "likes_count": 80,
                "is_verified": True,
            },
            {
                "username": "crystal_clear",
                "email": "crystal.clear@example.com",
                "display_name": "Crystal Clear",
                "bio": "Elegant and sophisticated performer. Focus on high-quality content and intimate connections.",
                "gender": "female",
                "age": 30,
                "country": "United States",
                "ethnicity": "Белая (Белый)",
                "hair_color": "blonde",
                "eye_color": "blue",
                "has_tattoos": True,
                "tattoos_description": "Small butterfly on ankle",
                "has_piercings": True,
                "piercings_description": "Ear and nose piercings",
                "breast_size": "large",
                "measurements": "36C-66-92",
                "height": 175,
                "weight": 60,
                "zodiac_sign": "Libra",
                "views_count": 55000,
                "subscribers_count": 200,
                "videos_count": 110,
                "likes_count": 150,
                "is_verified": True,
            },
        ]

        created_count = 0

        for model_data in test_models:
            # Create user
            user, created = User.objects.get_or_create(
                username=model_data["username"],
                defaults={
                    "email": model_data["email"],
                    "first_name": model_data["display_name"].split()[0],
                    "last_name": model_data["display_name"].split()[1]
                    if len(model_data["display_name"].split()) > 1
                    else "",
                },
            )

            if created:
                user.set_password("password123")
                user.save()
                self.stdout.write(f"Created user: {user.username}")

            # Create model
            model_data_copy = model_data.copy()
            # Remove user-specific fields
            model_data_copy.pop("username", None)
            model_data_copy.pop("email", None)

            model, created = Model.objects.get_or_create(
                user=user, defaults=model_data_copy
            )

            if created:
                created_count += 1
                self.stdout.write(f"Created model: {model.display_name}")
            else:
                self.stdout.write(f"Model already exists: {model.display_name}")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {created_count} test models")
        )
