import abc
from typing import List, NoReturn

from ..constants import MIGRATION_TABLE_BACKUP_FILE_NAME,\
    MIGRATION_TABLE_BACKUP_DIR_NAME,\
    MIGRATION_FILES_BACKUP_DIR_NAME
from ..exceptions import BackupError
from ..utils import BackupFile, Migration, BackupDir, AppMigrationsDir


class BaseBackup(abc.ABC):

    @abc.abstractmethod
    def backup(self):
        raise NotImplementedError


class MigrationsTableBackup(BaseBackup):

    def __init__(self):
        backup_directory = BackupDir(MIGRATION_TABLE_BACKUP_DIR_NAME)
        self.file_handler = BackupFile(
            directory=backup_directory,
            file_name=MIGRATION_TABLE_BACKUP_FILE_NAME
        )

    def backup(self) -> NoReturn:
        migrations_data = self.get_migrations_data_from_db()
        self._validate_backup()
        self.file_handler.write(data=migrations_data)

    @staticmethod
    def get_migrations_data_from_db() -> List[dict]:
        all_migrations = Migration.objects.iterator()
        data = []
        for migration in all_migrations:
            data.append(
                {field.name: getattr(migration, field.name, None)
                 for field in migration._meta.fields}
            )
        return data

    def _validate_backup(self) -> NoReturn:
        migrations_count_in_db = Migration.objects.count()
        migrations_count_in_file = len(self.get_migrations_data_from_db())

        if migrations_count_in_db != migrations_count_in_file:
            raise BackupError(f"There is an error in backup process. "
                              f"Apparently migrations count in db is: {migrations_count_in_db}, "
                              f"while its count in backup file is: {migrations_count_in_file}. "
                              f"We don't proceed any further, but you can take a backup yourself.")


class MigrationFilesBackup(BaseBackup):

    def __init__(self, app_name: str):
        self.app_name = app_name
        self.app_migrations_dir = AppMigrationsDir(app_name=app_name)
        self.migrations_backup_dir = BackupDir(MIGRATION_FILES_BACKUP_DIR_NAME, app_name)

    def backup(self) -> NoReturn:
        if not self.app_migrations_dir.has_migration:
            return

        self.app_migrations_dir.copy(destination=self.migrations_backup_dir.path)
