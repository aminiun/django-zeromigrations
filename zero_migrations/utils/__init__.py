import abc
import json
import os
from datetime import datetime, date
from pathlib import Path
from shutil import rmtree, copytree

from typing import NoReturn, List, Optional, Union

from django.apps import apps
from django.db.migrations.loader import MIGRATIONS_MODULE_NAME
from django.db.migrations.recorder import MigrationRecorder

from ..apps import ZeroMigrationsConfig

Migration = MigrationRecorder.Migration


class BaseDir(abc.ABC):

    def create(self) -> NoReturn:
        Path(self.path).mkdir(parents=True, exist_ok=True)

    def copy(self, destination: Union[Path, str]) -> NoReturn:
        copytree(self.path, destination, dirs_exist_ok=True)

    def get_files(self) -> List[str]:
        return os.listdir(self.path)

    @property
    @abc.abstractmethod
    def path(self):
        raise NotImplementedError


class BackupDir(BaseDir):
    BACKUP_DIR_NAME = "backups"

    def __init__(self, *dir_names):
        self._dir_names = dir_names

    def clear(self) -> NoReturn:
        rmtree(self.path, ignore_errors=True)

    def get_files_with_postfix(self, postfix: str = "") -> List[str]:
        return [
            str(dir_) for dir_ in self.get_files()
            if str(dir_).endswith(postfix)
        ]

    @property
    def path(self) -> Path:
        return self.app_dir_path / self.BACKUP_DIR_NAME / Path(*self._dir_names)

    @property
    def app_dir_path(self) -> Path:
        return Path(apps.get_app_config(ZeroMigrationsConfig.name).path)


class AppMigrationsDir(BaseDir):

    def __init__(self, app_name: str):
        self.app_name = app_name

    @property
    def path(self) -> Path:
        return Path(apps.get_app_config(app_label=self.app_name).path) / MIGRATIONS_MODULE_NAME

    @property
    def has_migration(self) -> bool:
        return any(file[0] not in '_~' for file in self.get_files())


class BackupFile:

    REVISION_START_FROM = "0001"

    def __init__(self, directory: BackupDir, file_name: str):
        self._file_name = file_name
        self.backup_dir = directory

        self._revision_num_len = len(self.REVISION_START_FROM)

    def write(self, data) -> NoReturn:
        self.backup_dir.create()

        def datetime_json_serialize(obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()

        with open(self.new_file_path, "w+") as f:
            json.dump(data, f, default=datetime_json_serialize)

    def read(self) -> List[dict]:
        def datetime_json_deserialize(obj: dict):
            for field, value in obj.items():
                try:
                    obj[field] = datetime.fromisoformat(value)
                except (ValueError, TypeError):
                    pass
            return obj

        with open(self.latest_file_path, "r") as f:
            return json.load(f, object_hook=datetime_json_deserialize)

    @property
    def new_file_path(self) -> Path:
        return self.backup_dir.path / self.next_revision

    @property
    def latest_file_path(self) -> Path:
        if self.latest_revision:
            return self.backup_dir.path / self.latest_revision

        return self.new_file_path

    @property
    def next_revision(self) -> str:
        latest_revision = self.latest_revision
        if not latest_revision:
            return f"{self.REVISION_START_FROM}_{self._file_name}"

        next_revision_number = self.make_next_revision_number()
        return f"{next_revision_number}{latest_revision[self._revision_num_len:]}"

    @property
    def latest_revision(self) -> Optional[str]:
        all_backups = self.backup_dir.get_files_with_postfix(postfix=self._file_name)
        if not all_backups:
            return None

        return sorted(all_backups)[-1]

    def make_next_revision_number(self) -> str:
        new_revision_number = int(self.latest_revision[:self._revision_num_len]) + 1
        return "%0{revision_num_len}d".format(revision_num_len=self._revision_num_len) % (new_revision_number,)
