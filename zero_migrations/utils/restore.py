import abc

from django.db import transaction
from typing import List, NoReturn

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
    def restore(self) -> NoReturn:
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

    def __init__(self, app_name: str):
        self.app_name = app_name
        self.app_migrations_dir = AppMigrationsDir(app_name=app_name)
        self.migrations_backup_dir = BackupDir(MIGRATION_FILES_BACKUP_DIR_NAME, app_name)

    def restore(self) -> NoReturn:
        self.migrations_backup_dir.copy(destination=self.app_migrations_dir.path)
        self.migrations_backup_dir.clear()
