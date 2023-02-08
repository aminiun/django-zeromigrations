from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "Fake zero migrations"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        pass
