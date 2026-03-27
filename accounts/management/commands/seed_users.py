import random
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User, Profile


FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael",
    "Linda", "William", "Barbara", "David", "Susan", "Richard", "Jessica",
    "Joseph", "Sarah", "Thomas", "Karen", "Charles", "Lisa",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
]

BIOS = [
    "Passionate about technology and innovation.",
    "Avid reader and coffee enthusiast.",
    "Lover of travel and new experiences.",
    "Fitness junkie and outdoor adventurer.",
    "Creative thinker with a curious mind.",
    "Music lover and amateur guitarist.",
    "Foodie exploring cuisines from around the world.",
    "Night owl with a passion for stargazing.",
    "Dog person. Always.",
    "Just here to learn and grow.",
]

LOCATIONS = [
    "Lagos, Nigeria", "New York, USA", "London, UK", "Nairobi, Kenya",
    "Toronto, Canada", "Sydney, Australia", "Berlin, Germany", "Paris, France",
    "Dubai, UAE", "Accra, Ghana",
]

WEBSITES = [
    "https://example.com", "https://myblog.io", "https://portfolio.dev",
    "https://personal.site", "",
]


class Command(BaseCommand):
    help = "Seed the database with dummy users"

    def add_arguments(self, parser):
        parser.add_argument(
            "count",
            type=int,
            help="Number of dummy users to create",
        )
        parser.add_argument(
            "--password",
            type=str,
            default="Password123!",
            help="Password for all seeded users (default: Password123!)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all non-superuser users before seeding",
        )
        parser.add_argument(
            "--admin",
            action="store_true",
            help="Also create a superuser admin@gnoza.dev with the given --password",
        )

    def handle(self, *args, **options):
        count = options["count"]
        password = options["password"]
        clear = options["clear"]

        if count <= 0:
            raise CommandError("Count must be a positive integer.")

        if clear:
            deleted, _ = User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing users."))

        if options["admin"]:
            admin_email = "admin@gnoza.dev"
            if User.objects.filter(email=admin_email).exists():
                self.stdout.write(self.style.WARNING(f"Admin {admin_email} already exists, skipping."))
            else:
                User.objects.create_superuser(
                    email=admin_email,
                    password=password,
                    first_name="Admin",
                    last_name="Gnoza",
                    is_active=True,
                )
                self.stdout.write(self.style.SUCCESS(f"Superuser created: {admin_email}"))

        created_count = 0

        with transaction.atomic():
            for i in range(count):
                first_name = random.choice(FIRST_NAMES)
                last_name = random.choice(LAST_NAMES)
                email = f"{first_name.lower()}.{last_name.lower()}.{i}@seed.gnoza.dev"

                if User.objects.filter(email=email).exists():
                    self.stdout.write(self.style.WARNING(f"Skipping duplicate: {email}"))
                    continue

                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True,
                )

                # Profile is auto-created by post_save signal.
                # Update with extra dummy data.
                profile = user.profile
                profile.bio = random.choice(BIOS)
                profile.location = random.choice(LOCATIONS)
                profile.website = random.choice(WEBSITES)
                profile.date_of_birth = date(
                    random.randint(1970, 2000),
                    random.randint(1, 12),
                    random.randint(1, 28),
                )
                profile.save()

                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully seeded {created_count} users.")
        )