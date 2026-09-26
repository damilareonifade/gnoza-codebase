from django.db import migrations


CATEGORIES = [
    ("national", "National"),
    ("international", "International"),
    ("sport", "Sport"),
    ("lifestyle", "Lifestyle"),
    ("business", "Business"),
    ("health", "Health"),
    ("fashion", "Fashion"),
    ("technology", "Technology"),
    ("science", "Science"),
    ("art", "Art"),
    ("politics", "Politics"),
]


def seed_topics(apps, schema_editor):
    Topic = apps.get_model("topics", "Topic")
    UserTopic = apps.get_model("topics", "UserTopic")
    UserPreference = apps.get_model("accounts", "UserPreference")

    for order, (slug, name) in enumerate(CATEGORIES):
        if not Topic.objects.filter(slug=slug).exists() and not Topic.objects.filter(name=name).exists():
            Topic.objects.create(slug=slug, name=name, order=order)

    # Keep topics users already chose as their explicit picks.
    topics_by_slug = {t.slug: t for t in Topic.objects.all()}
    for prefs in UserPreference.objects.exclude(preferred_topics=[]):
        for value in prefs.preferred_topics or []:
            topic = topics_by_slug.get(str(value).strip().lower())
            if topic:
                UserTopic.objects.get_or_create(
                    user_id=prefs.user_id, topic=topic, defaults={"is_saved": True}
                )


class Migration(migrations.Migration):

    dependencies = [
        ("topics", "0001_initial"),
        ("accounts", "0004_user_username"),
    ]

    operations = [
        migrations.RunPython(seed_topics, migrations.RunPython.noop),
    ]
