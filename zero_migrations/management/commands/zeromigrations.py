import site
from typing import List, NoReturn
from functools import lru_cache

from django.apps import apps
from django.core.management import BaseCommand, call_command

from zero_migrations.utils import BackupDir, AppMigrationsDir, Migration
from zero_migrations.utils.backup import MigrationsTableBackup, MigrationFilesBackup
from zero_migrations.utils.restore import MigrationFilesRestore, MigrationsTableRestore


class Command(BaseCommand):
    help = "zeromigrations command to set migration files zero."

    MAKE_BACKUP = 1
    RESTORE_LAST_BACKUP = 2
    PROCEED = 3

    DELETE_MIGRATION_FILES = 1
    KEEP_MIGRATION_FILES = 2

    def add_arguments(self, parser):
        parser.add_argument(
            "--backup-path",
            help="Backup path to save backup files in it.",
        )
        parser.add_argument(
            "--use-fake-zero",
            action="store_true",
            required=False,
            help="Use django --fake zero command for migration deletion from DB.",
        )

    def handle(self, *args, **options):
        use_fake_zero = options.get("use-fake-zero")

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
            self.zero_migrations(use_fake_zero=use_fake_zero)

    def make_backup(self) -> NoReturn:
        """
        Making a backup for django_migrations table and migration files in each app.
        These backups will be used if any failure happened in zero_migrations process.
        """
        MigrationsTableBackup().backup()

        for app in self.get_local_apps():
            MigrationFilesBackup(app_name=app).backup()

        proceed_perm = input(
            self.style.SUCCESS(
                "Backup made successfully!.\n"
                f"Backups are in: {BackupDir().path}.\n"
                f"Shall I set migrations zero now? (Y/n) "
            )
        ) or "Y"
        if proceed_perm.lower() == "y":
            self.zero_migrations()

    def zero_migrations(self, use_fake_zero=None):
        """
        Settings migrations zero.
        This process includes of 4 steps:
            1- Running `migrate --fake {app_name} zero` for each app
            2- Removing migrations files.
            3- Running `makemigrations` to make new initial migrations.
            4- Running `migrate --fake-initial` to fake made initial migrations.
        In case of any failure, it tries to restore the latest backup.
        """
        try:
            self.stdout.write(self.style.WARNING("Migrate zero each app:"))
            for app in self.get_all_apps():
                self.stdout.write(self.style.WARNING(f"App name: {app}"))
                if use_fake_zero:
                    call_command("migrate", "--fake", app, "zero", force_color=True)
                else:
                    Migration.objects.filter(app=app).delete()

            self.stdout.write(self.style.WARNING("Removing migrations:"))
            for app in self.get_local_apps():
                AppMigrationsDir(app_name=app).clear()
                self.stdout.write(self.style.SUCCESS(f"Removed migrations of {app}"))

            self.stdout.write(self.style.WARNING("Making migrations:"))
            call_command("makemigrations", force_color=True)

            for app in self.get_local_apps():
                AppMigrationsDir(app_name=app).reload()

            self.stdout.write(self.style.WARNING("Migrate with fake initial:"))
            call_command("migrate", "--fake", force_color=True)

        except Exception as err:
            self.stderr.write(
                self.style.ERROR(
                    f"Process failed because of {err}.\n"
                )
            )
            self.restore()

    def restore(self):
        """
        Restoring the latest backup, if any failure has happened or the user wants to do it itself.
        First django_migrations table would be restored and after that, migrations files would be restored.
        For migration files restoring, user has to decide whether his/her current migrations files
            should be deleted or not. If he/her decided not to delete his/her current migration files,
            then backup files would be replaced
        Note that backup data would be clear after restoring.
        """
        self.stdout.write(
            self.style.WARNING("Restoring ...")
        )
        MigrationsTableRestore().restore()
        self.stdout.write(
            self.style.SUCCESS("django_migrations table restored.")
        )
        choice = int(input(
            self.style.WARNING(
                "Trying to restore migration file.\n"
                f"1- Delete my current migration files and restore.\n"
                f"2- Keep my current migration files and replace restore.\n"
            )
        ))
        delete_migrations = choice == self.DELETE_MIGRATION_FILES
        for app in self.get_local_apps():
            migration_files_restore = MigrationFilesRestore(app_name=app)
            if migration_files_restore.migrations_backup_dir.has_migration:
                if delete_migrations:
                    migration_files_restore.app_migrations_dir.clear()
                migration_files_restore.restore()
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"Couldn't find any backup for app {app} in"
                        f"{migration_files_restore.migrations_backup_dir.path}."
                    )
                )

    @lru_cache
    def get_local_apps(self) -> List[str]:
        """
        Get all user django apps.
        Apps that have been installed and are not written by user, would be excluded. This is because we don't want to
            set third-party packages migrations zero.
        :return: List of user apps names.
        """
        installed_app_path = site.getsitepackages()[0]
        return [
            app.name for app in apps.get_app_configs()
            if not str(app.path).startswith(str(installed_app_path))
        ]

    @lru_cache
    def get_all_apps(self) -> List[str]:
        """
        Get all django apps, including admin, auth, ...
        """
        return [
            app.name.split(".")[-1] for app in apps.get_app_configs()
        ]
