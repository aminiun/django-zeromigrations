import abc

from django.apps import apps
from django.db import transaction
from typing import List

from .. import app_settings
from ..constants import MIGRATION_TABLE_BACKUP_DIR_NAME, MIGRATION_TABLE_BACKUP_FILE_NAME, \
    MIGRATION_FILES_BACKUP_DIR_NAME
from ..utils import BackupFile, Migration, BackupDir, AppMigrationsDir


class BaseRestore(abc.ABC):

    @abc.abstractmethod
    def restore(self):
        raise NotImplementedError


class MigrationsTableRestore(BaseRestore):

    def __init__(self):
        backup_dir = BackupDir(MIGRATION_TABLE_BACKUP_DIR_NAME)
        self.file_handler = BackupFile(
            directory=backup_dir,
            file_name=MIGRATION_TABLE_BACKUP_FILE_NAME
        )

    @transaction.atomic
    def restore(self):
        backup_migrations = self.get_migrations_data_from_backup()
        Migration.objects.all().delete()
        Migration.objects.bulk_create(backup_migrations)

    def get_migrations_data_from_backup(self) -> List[Migration]:
        migrations_data = self.file_handler.read()
        backup_migrations = []
        for migration in migrations_data:
            backup_migrations.append(
                Migration(**migration)
            )

        return backup_migrations


class MigrationFilesRestore(BaseRestore):

    def restore(self):
        for app in apps.get_app_configs():
            if app.name in app_settings.IGNORE_APPS:
                continue

            app_migrations_dir = AppMigrationsDir(app_name=app.name)
            migrations_backup_dir = BackupDir(MIGRATION_FILES_BACKUP_DIR_NAME, app.name)

            if not app_migrations_dir.has_migration:
                continue

            migrations_backup_dir.copy(destination=app_migrations_dir.path)
