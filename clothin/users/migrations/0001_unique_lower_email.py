from django.db import migrations


def check_no_existing_duplicates(apps, schema_editor):
    from django.db.models import Count
    from django.db.models.functions import Lower

    User = apps.get_model('auth', 'User')
    dupes = (
        User.objects.exclude(email='')
        .annotate(lower_email=Lower('email'))
        .values('lower_email')
        .annotate(c=Count('id'))
        .filter(c__gt=1)
    )
    if dupes.exists():
        raise RuntimeError(
            f'Duplicate emails exist, resolve manually before migrating: {list(dupes)}'
        )


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(check_no_existing_duplicates, migrations.RunPython.noop),
        migrations.RunSQL(
            sql="CREATE UNIQUE INDEX unique_lower_email ON auth_user (LOWER(email)) WHERE email <> '';",
            reverse_sql="DROP INDEX unique_lower_email;",
        ),
    ]
