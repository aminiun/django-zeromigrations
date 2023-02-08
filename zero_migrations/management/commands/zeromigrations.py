from django.core.management import BaseCommand

from zero_migrations.backup import MigrationBackup


class Command(BaseCommand):
    help = "Fake zero migrations"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        MigrationBackup().backup()
