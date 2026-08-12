from django.db import migrations, models
from django.db.models import Q


def backfill_usernames(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    seen = set(
        User.objects.exclude(username__isnull=True)
        .exclude(username="")
        .values_list("username", flat=True)
    )
    for user in User.objects.filter(Q(username__isnull=True) | Q(username="")):
        base = user.email.split("@")[0]
        candidate = base
        suffix = 1
        while candidate in seen:
            candidate = f"{base}{suffix}"
            suffix += 1
        seen.add(candidate)
        user.username = candidate
        user.save(update_fields=["username"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_remove_userpreference_full_name_delete_profile"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="username",
            field=models.CharField(max_length=150, null=True, unique=True),
        ),
        migrations.RunPython(backfill_usernames, noop),
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(max_length=150, unique=True, db_index=True),
        ),
    ]
