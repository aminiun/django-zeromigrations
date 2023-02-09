import json
import os
from datetime import datetime, date
from pathlib import Path

from typing import NoReturn, List

from django.db.migrations.recorder import MigrationRecorder

Migration = MigrationRecorder.Migration


class BackupFile:

    BACKUP_DIR_NAME = "backups"
    REVISION_START_FROM = "0001"

    def __init__(self, dir_name: str, file_name: str):
        self._dir_name = dir_name
        self._file_name = file_name

        self._revision_num_len = len(self.REVISION_START_FROM)

        Path(self.backup_dir_path).mkdir(parents=True, exist_ok=True)

    def write(self, data) -> NoReturn:
        def datetime_json_serialize(obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()

        with open(self.new_file_path, "w") as f:
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
    def new_file_path(self):
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
    def latest_file_path(self):
        if self.latest_revision:
            return self.backup_dir_path / self.latest_revision

        return self.new_file_path

    @property
    def latest_revision(self):
        all_backups = [
            str(dir_) for dir_ in os.listdir(self.backup_dir_path)
            if str(dir_).endswith(self._file_name)
        ]
        if not all_backups:
            return None

        return sorted(all_backups)[-1]

    @property
    def backup_dir_path(self):
        return self.app_dir_path / self.BACKUP_DIR_NAME / self._dir_name

    @property
    def app_dir_path(self):
        return Path(__file__).parent.parent
