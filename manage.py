import os
import sys

import django
from django.conf import settings
from django.core.management import execute_from_command_line

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "zero_migrations"))

if __name__ == "__main__":
    settings.configure(
        BASE_DIR=BASE_DIR,
        DEBUG=True,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
            }
        },
        INSTALLED_APPS=(
            "django.contrib.contenttypes",
            "zero_migrations",
        ),
        TIME_ZONE="UTC",
        USE_TZ=True,
    )
    django.setup()
    execute_from_command_line(sys.argv)
