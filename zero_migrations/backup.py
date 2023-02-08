import abc
import json
import os
from pathlib import Path

from django.db.migrations.recorder import MigrationRecorder
from typing import NoReturn

Migration = MigrationRecorder.Migration


class BackupFile:

    BACKUP_DIR_NAME = "backups"
    REVISION_START_FROM = "0001"

    def __init__(self, dir_name: str, file_name: str):
        self._dir_name = dir_name
        self._file_name = file_name

        self._revision_num_len = len(self.REVISION_START_FROM)

    def write(self, data) -> NoReturn:
        with open(self.file_path, "w") as f:
            json.dump(f, data)

    def read(self) -> dict:
        with open(self.file_path, "r") as f:
            return json.load(f)

    @property
    def file_path(self):
        return self.backup_dir_path / self.next_revision

    @property
    def next_revision(self):
        latest_revision = self.latest_revision
        if not latest_revision:
            return f"{self.REVISION_START_FROM}_{self._file_name}"

        next_revision_number = self.make_next_revision_number()
        return f"{next_revision_number}{latest_revision[self._revision_num_len:]}"

    def make_next_revision_number(self) -> str:
        new_revision_number = int(self.latest_revision[:self._revision_num_len]) + 1
        return "%0{revision_num_len}d".format(revision_num_len=self._revision_num_len) % (new_revision_number,)

    @property
    def latest_revision(self):
        all_backups = [
            dir_ for dir_ in os.listdir(self.backup_dir_path)
            if dir_.endswith(self._file_name)
        ]
        if not all_backups:
            return None

        return sorted(all_backups)[-1]

    @property
    def backup_dir_path(self):
        return self.app_dir_path / self.BACKUP_DIR_NAME / self._dir_name

    @property
    def app_dir_path(self):
        return Path(__file__).parent


class BaseBackup(abc.ABC):

    @abc.abstractmethod
    def backup(self):
        raise NotImplementedError


class MigrationBackup(BaseBackup):

    BACKUP_FILE_NAME = "backup_migrations_table.json"
    BACKUP_DIRECTORY = "backups"

    def backup(self):
        backup_path = os.path.dirname(os.path.realpath(__file__)) + "/backups/0001_backup.json"
        # TODO Iterator
        old_migrations = Migration.objects.all()
        data = [
            {field.name: getattr(migration, field.name, None) for field in migration._meta.fields}
            for migration in old_migrations
        ]
        with open(backup_path, "a") as f:
            f.write(json.dumps(data, default=str))
            # migration._meta.fields

    def backup_directory_full_path(self):
        pass
