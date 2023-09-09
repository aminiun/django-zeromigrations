import abc
import json
import os
import sys
from datetime import datetime, date
from functools import lru_cache
from importlib import reload, import_module
from pathlib import Path
from shutil import rmtree, copytree

from typing import NoReturn, List, Optional, Union

from django.apps import apps
from django.db.migrations.loader import MIGRATIONS_MODULE_NAME
from django.db.migrations.recorder import MigrationRecorder

from ..apps import ZeroMigrationsConfig

Migration = MigrationRecorder.Migration


class BaseDir(abc.ABC):
    """
    Base class for directories.
    Each subclass should implement path() property, as operations happen in that path.

    -----
    Base operation:
        create: For creating directory in returned path from `path` property.
        copy: To copy a directory to a destination. This method is used when we want to copy our files(like backups).
        get_files: Return all files in a directory.
    """

    def create(self) -> NoReturn:
        Path(self.path).mkdir(parents=True, exist_ok=True)

    def copy(self, destination: Union[Path, str]) -> NoReturn:
        copytree(self.path, destination, dirs_exist_ok=True)

    @property
    def has_migration(self) -> bool:
        """True if there is at least one file in the directory that doesn't start with '_' or '~'."""
        return any(file[0] not in '_~' for file in self.get_files())

    def get_files(self) -> List[str]:
        try:
            return os.listdir(self.path)
        except FileNotFoundError:
            return []

    @property
    @abc.abstractmethod
    def path(self):
        raise NotImplementedError


class BackupDir(BaseDir):
    """
    A class for backup directory.
    As backup dir name is set to "backups" by default, the path would be sth like: /home/.../zero_migrations/backups
    You can pass multiple directory names to its constructor, and they would be joined together in final path.

    -----
    Usage Examples:
        bkp_dir = BackupDir("test")
        bkp_dir.path    --->    /home/.../zero_migrations/backups/test

        bkp_dir = BackupDir("first", "second")
        bkp_dir.path    --->    /home/.../zero_migrations/backups/first/second
    """
    BACKUP_DIR_NAME = "backups"

    def __init__(self, *dir_names):
        self._base_path = self._extract_backup_path()
        self._dir_names = dir_names

    def _extract_backup_path(self) -> Path:
        for arg in sys.argv:
            if arg.startswith("--backup-path"):
                return Path(arg.split("=")[1]) / self.BACKUP_DIR_NAME

        return self.app_dir_path / self.BACKUP_DIR_NAME

    def clear(self) -> NoReturn:
        """
        Cleaning all files inside the directory.
        As the files have to be backup files, it's OK to remove all at once.
        This method is used when the backup is used, and we want to clear our old backups.
        """
        rmtree(self.path, ignore_errors=True)

    def get_files_with_postfix(self, postfix: str = "") -> List[str]:
        """
        Filtering files inside the directory, base on their postfix.
        This method is used when we want to get all files that have our postfix like `migration_backup.json`

        -----
        Usage Example:
            Assume self.get_files() return ["test.json", "test.txt"], then:
            self.get_files_with_postfix("json")     --->    ["test.json"]
        """
        return [
            str(dir_) for dir_ in self.get_files()
            if str(dir_).endswith(postfix)
        ]

    @property
    @lru_cache
    def path(self) -> Path:
        return self._base_path / Path(*self._dir_names)

    @property
    def app_dir_path(self) -> Path:
        return Path(apps.get_app_config(ZeroMigrationsConfig.name).path)


class AppMigrationsDir(BaseDir):

    def __init__(self, app_name: str):
        self.app_name = app_name

    def clear(self) -> NoReturn:
        """
        Cleaning files inside the migrations' directory.
        As it is not our directory, and it is user app migrations directory, we just delete *.py to prevent deleting
            user's other files.
        This method is used when we have run `migrate --fake app zero` and we want to delete old migrations.
        """
        for file_name in self.get_files():
            if file_name != "__init__.py" and file_name.endswith(".py"):
                os.remove(self.path / file_name)

    def reload(self):
        """
        Reloads the migrations of the app.
        """
        for file_name in self.get_files():
            if file_name.endswith(".py"):
                module_name = f"{self.app_name}.migrations.{file_name[:-3]}"
                if module_name in sys.modules:
                    reload(import_module(module_name))

    @property
    @lru_cache
    def path(self) -> Path:
        return Path(apps.get_app_config(app_label=self.app_name).path) / MIGRATIONS_MODULE_NAME


class BackupFile:
    """
    This class is for handling `django_migrations` backup files issues.

    For now, we keep old backups of `django_migrations` too. For handling the duplicate issue,
        we use a number as a prefix for our backup files, called REVISION_NUMBER. This number increases based on last
        backup file in the directory, and if no files is in there, it is just REVISION_START_FROM.

    -----
    Usage Examples:
        Assume that we have a backup file called `0001_migration_backup.json` in backup directory, then:
        bkp_dir = BackupDir("migrations")
        bkp_file = BackupFile(directory=bkp_dir, file_name="test")
        bkp_file.latest_file_path   --->    /home/.../zero_migrations/backups/migrations/0001_migration_backup.json
        bkp_file.new_file_path   --->    /home/.../zero_migrations/backups/migrations/0002_migration_backup.json
        bkp_file.read()     ---> Reads from latest_file_path
        bkp_file.write(data)     ---> Writes in new_file_path
    """

    REVISION_START_FROM = "0001"

    def __init__(self, directory: BackupDir, file_name: str):
        self._file_name = file_name
        self.backup_dir = directory

        self._revision_num_len = len(self.REVISION_START_FROM)

    def write(self, data: List[dict]) -> NoReturn:
        """
        For writing in new_file_path (file with new revision).
        First, it makes sure the backup directory exists via invoking `create()` on self.backup_dir.
        Then, it invokes `json.dump` to get json of passed data.
        Note that because data has datetime in it (applied field in migration record) and `json.dump` is unable to
            serialize that, we change datetime objects to `iso format`.
        """
        self.backup_dir.create()

        # Changing datetime to iso format, so that json.dump can serialize it.
        def datetime_json_serialize(obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()

        with open(self.new_file_path, "w+") as f:
            json.dump(data, f, default=datetime_json_serialize)

    def read(self) -> List[dict]:
        """
        For reading from latest_file_path (file with the latest revision).
        It invokes `json.load` to get dict of json data.
        Note that because the json data has iso format in it, and we want datetime object instead of that,
            we change iso format to datetime object as a hook in `json.load`.
        """

        # Changing iso format to datetime object.
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
        """
        Getting next revision to write on.
        If the directory has no backup file already, then we don't have latest_revision. In this scenario,
            the next_revision is going to be first revision (self.REVISION_START_FROM).
        Otherwise, next_revision is the latest_revision + 1.
        """
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

        # As our backup files have the same postfix, the last file name in the sorted list of file names,
        # is our latest_revision.
        return sorted(all_backups)[-1]

    def make_next_revision_number(self) -> str:
        new_revision_number = int(self.latest_revision[:self._revision_num_len]) + 1
        return "%0{revision_num_len}d".format(revision_num_len=self._revision_num_len) % (new_revision_number,)
