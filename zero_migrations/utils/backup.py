import abc
from typing import List

from zero_migrations.constants import MIGRATION_TABLE_BACKUP_FILE_NAME, MIGRATION_TABLE_BACKUP_DIR_NAME
from zero_migrations.exceptions import BackupError
from zero_migrations.utils import BackupFile, Migration


class BaseBackup(abc.ABC):

    @abc.abstractmethod
    def backup(self):
        raise NotImplementedError


class MigrationBackup(BaseBackup):

    def __init__(self):
        self.file_handler = BackupFile(
            dir_name=MIGRATION_TABLE_BACKUP_DIR_NAME,
            file_name=MIGRATION_TABLE_BACKUP_FILE_NAME
        )

    def backup(self):
        migrations_data = self.get_migrations_data_from_db()
        self._validate_backup()
        self.file_handler.write(data=migrations_data)

    @staticmethod
    def get_migrations_data_from_db() -> List[dict]:
        all_migrations = Migration.objects.iterator()
        data = []
        for migration in all_migrations:
            data.append(
                {field.name: getattr(migration, field.name, None) for field in migration._meta.fields}
            )
        return data

    def _validate_backup(self):
        migrations_count_in_db = Migration.objects.count()
        migrations_count_in_file = len(self.get_migrations_data_from_db())

        if migrations_count_in_db != migrations_count_in_file:
            raise BackupError(f"There is an error in backup process. "
                              f"Apparently migrations count in db is: {migrations_count_in_db}, "
                              f"while its count in backup file is: {migrations_count_in_file}. "
                              f"We don't proceed any further, but you can take a backup yourself.")
