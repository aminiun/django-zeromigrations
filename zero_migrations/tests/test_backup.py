from pathlib import Path
from unittest.mock import patch

from django.test import TestCase

from zero_migrations.backup import BackupFile


class TestBackupFile(TestCase):

    def test_backup_dir(self):
        backup_file = BackupFile(dir_name="migrations", file_name="test")

        self.assertEqual(
            str(backup_file.backup_dir_path),
            str(Path(__file__).parent.parent / BackupFile.BACKUP_DIR_NAME / "migrations")
        )

    @patch("zero_migrations.backup.os.listdir")
    def test_latest_revision_without_any_file_in_dir(self, mock_listdir):
        mock_listdir.return_value = []
        backup_file = BackupFile(dir_name="migrations", file_name="test")

        self.assertIsNone(backup_file.latest_revision)

    @patch("zero_migrations.backup.os.listdir")
    def test_latest_revision_with_files_in_dir(self, mock_listdir):
        mock_listdir.return_value = ["0001_sth.json", "0002_sth.json"]
        backup_file = BackupFile(dir_name="migrations", file_name="sth.json")

        self.assertEqual(str(backup_file.latest_revision), "0002_sth.json")

    @patch("zero_migrations.backup.os.listdir")
    def test_new_revision_without_any_file_in_dir(self, mock_listdir):
        mock_listdir.return_value = []
        backup_file = BackupFile(dir_name="migrations", file_name="test")

        self.assertEqual(str(backup_file.next_revision), f"{BackupFile.REVISION_START_FROM}_test")

    @patch("zero_migrations.backup.os.listdir")
    def test_new_revision_with_files_in_dir(self, mock_listdir):
        mock_listdir.return_value = ["0001_sth.json", "0002_sth.json"]
        backup_file = BackupFile(dir_name="migrations", file_name="sth.json")

        self.assertEqual(str(backup_file.next_revision), "0003_sth.json")

    @patch("zero_migrations.backup.os.listdir")
    def test_file_path_without_any_file_in_dir(self, mock_listdir):
        mock_listdir.return_value = []
        backup_file = BackupFile(dir_name="migrations", file_name="test")

        self.assertEqual(
            str(backup_file.file_path),
            str(backup_file.backup_dir_path / f"{BackupFile.REVISION_START_FROM}_test")
        )

    @patch("zero_migrations.backup.os.listdir")
    def test_file_path_with_files_in_dir(self, mock_listdir):
        mock_listdir.return_value = ["0001_sth.json", "0002_sth.json"]
        backup_file = BackupFile(dir_name="migrations", file_name="sth.json")

        self.assertEqual(
            str(backup_file.file_path),
            str(backup_file.backup_dir_path / "0003_sth.json")
        )
