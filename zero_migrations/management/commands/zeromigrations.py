from functools import lru_cache

from django.apps import apps
from django.core.management import BaseCommand, call_command
from typing import List

from zero_migrations.app_settings import IGNORE_APPS
from zero_migrations.utils import BackupDir, AppMigrationsDir
from zero_migrations.utils.backup import MigrationsTableBackup, MigrationFilesBackup
from zero_migrations.utils.restore import MigrationFilesRestore, MigrationsTableRestore


class Command(BaseCommand):
    help = "Fake zero migrations"

    MAKE_BACKUP = 1
    RESTORE_LAST_BACKUP = 2
    PROCEED = 3

    DELETE_MIGRATION_FILES = 1
    KEEP_MIGRATION_FILES = 2

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        choice = int(input(
            self.style.WARNING(
                "I suggest to make a backups from both your "
                "migrations and django_migrations table (just in case).\n"
                f"1- make backup\n"
                f"2- restore last backup\n"
                f"3- just proceed\n"
            )
        ))
        if choice == self.MAKE_BACKUP:
            self.make_backup()
        if choice == self.RESTORE_LAST_BACKUP:
            self.restore()
        if choice == self.PROCEED:
            self.zero_migrations()

    def make_backup(self):
        MigrationsTableBackup().backup()

        for app in self.get_apps():
            MigrationFilesBackup(app_name=app).backup()

        proceed_perm = input(
            self.style.SUCCESS(
                "Backup made successfully!.\n"
                f"Backups are in: {BackupDir().path}.\n"
                f"Shall I proceed ? (y/n) "
            )
        )
        if proceed_perm == "y":
            self.zero_migrations()

    def zero_migrations(self):
        try:
            self.stdout.write(self.style.WARNING("Migrate zero each app:"))
            for app in self.get_apps():
                self.stdout.write(self.style.WARNING(f"App name: {app}"))
                call_command("migrate", "--fake", app, "zero", force_color=True)

            self.stdout.write(self.style.WARNING("Removing migrations:"))
            for app in self.get_apps():
                AppMigrationsDir(app_name=app).clear()
                self.stdout.write(self.style.SUCCESS(f"Removed migrations of {app}"))

            self.stdout.write(self.style.WARNING("Making migrations:"))
            call_command("makemigrations", force_color=True)

            self.stdout.write(self.style.WARNING("Migrate with fake initial:"))
            call_command("migrate", "--fake-initial", force_color=True)

        except Exception as err:
            self.stderr.write(
                self.style.ERROR(
                    f"Process failed because of {err}.\n"
                )
            )
            self.restore()

    def restore(self):
        self.stdout.write(
            self.style.WARNING("Restoring ...")
        )
        MigrationsTableRestore().restore()
        self.stdout.write(
            self.style.SUCCESS("django_migrations table restored.")
        )
        choice = input(
            self.style.WARNING(
                "Trying to restore migration file.\n"
                f"1- Delete my current migration files and restore.\n"
                f"2- Keep my current migration files and replace restore.\n"
            )
        )
        delete_migrations = True if choice == self.DELETE_MIGRATION_FILES else False
        for app in self.get_apps():
            migration_files_restore = MigrationFilesRestore(app_name=app)
            if delete_migrations:
                migration_files_restore.app_migrations_dir.clear()
            migration_files_restore.restore()

    @lru_cache
    def get_apps(self) -> List[str]:
        return [
            app.name for app in apps.get_app_configs()
            if app.name not in IGNORE_APPS
        ]
