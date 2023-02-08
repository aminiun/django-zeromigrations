from datetime import datetime
from pathlib import Path
from shutil import rmtree
from unittest.mock import patch

from django.db.migrations.recorder import MigrationRecorder
from django.test import TestCase
from django.utils.timezone import now

from zero_migrations.backup import BackupFile, MigrationBackup


class TestBackupFile(TestCase):

    def setUp(self) -> None:
        self.test_backup_dir_name = "test"
        self.backup_file = BackupFile(dir_name=self.test_backup_dir_name, file_name="test.json")

    def test_backup_dir(self):
        self.assertEqual(
            str(self.backup_file.backup_dir_path),
            str(Path(__file__).parent.parent / BackupFile.BACKUP_DIR_NAME / self.test_backup_dir_name)
        )

    @patch("zero_migrations.backup.os.listdir")
    def test_latest_revision_without_any_file_in_dir(self, mock_listdir):
        mock_listdir.return_value = []

        self.assertIsNone(self.backup_file.latest_revision)

    @patch("zero_migrations.backup.os.listdir")
    def test_latest_revision_with_files_in_dir(self, mock_listdir):
        mock_listdir.return_value = ["0001_test.json", "0002_test.json"]

        self.assertEqual(str(self.backup_file.latest_revision), "0002_test.json")

    @patch("zero_migrations.backup.os.listdir")
    def test_new_revision_without_any_file_in_dir(self, mock_listdir):
        mock_listdir.return_value = []

        self.assertEqual(str(self.backup_file.next_revision), f"{BackupFile.REVISION_START_FROM}_test.json")

    @patch("zero_migrations.backup.os.listdir")
    def test_new_revision_with_files_in_dir(self, mock_listdir):
        mock_listdir.return_value = ["0001_test.json", "0002_test.json"]

        self.assertEqual(str(self.backup_file.next_revision), "0003_test.json")

    @patch("zero_migrations.backup.os.listdir")
    def test_new_file_path_without_any_file_in_dir(self, mock_listdir):
        mock_listdir.return_value = []

        self.assertEqual(
            str(self.backup_file.new_file_path),
            str(self.backup_file.backup_dir_path / f"{BackupFile.REVISION_START_FROM}_test.json")
        )

    @patch("zero_migrations.backup.os.listdir")
    def test_new_file_path_with_files_in_dir(self, mock_listdir):
        mock_listdir.return_value = ["0001_test.json", "0002_test.json"]

        self.assertEqual(
            str(self.backup_file.new_file_path),
            str(self.backup_file.backup_dir_path / "0003_test.json")
        )

    def test_write_data(self):
        migrations_data = [
            {
                "id": 1,
                "app": "test",
                "name": "test",
                "applied": now()
            },
            {
                "id": 2,
                "app": "test1",
                "name": "test1",
                "applied": now()
            }
        ]
        self.backup_file.write(data=migrations_data)

        written_data = self.backup_file.read()

        self.assertEqual(written_data[0]["id"], 1)
        self.assertEqual(written_data[0]["app"], "test")
        self.assertEqual(written_data[0]["name"], "test")
        self.assertTrue(isinstance(written_data[0]["applied"], datetime))

        self.assertEqual(written_data[1]["id"], 2)
        self.assertEqual(written_data[1]["app"], "test1")
        self.assertEqual(written_data[1]["name"], "test1")
        self.assertTrue(isinstance(written_data[1]["applied"], datetime))

    def tearDown(self) -> None:
        rmtree(self.backup_file.backup_dir_path, ignore_errors=True)


class TestBackupMigrations(TestCase):

    def test_get_migrations_data_from_db(self):
        migration_1 = MigrationRecorder.Migration.objects.create(app="test1", name="test1")
        migration_2 = MigrationRecorder.Migration.objects.create(app="test2", name="test2")

        migrations = MigrationBackup.get_migrations_data_from_db()

        self.assertEqual(migrations[0]["id"], migration_1.id)
        self.assertEqual(migrations[0]["app"], migration_1.app)
        self.assertEqual(migrations[0]["name"], migration_1.name)
        self.assertEqual(migrations[0]["applied"], migration_1.applied)

        self.assertEqual(migrations[1]["id"], migration_2.id)
        self.assertEqual(migrations[1]["app"], migration_2.app)
        self.assertEqual(migrations[1]["name"], migration_2.name)
        self.assertEqual(migrations[1]["applied"], migration_2.applied)

    @patch("zero_migrations.backup.BackupFile.read")
    def test_get_migrations_data_from_backup(self, mock_read):
        mock_read.return_value = [
            {
                "id": 1,
                "app": "test",
                "name": "test",
                "applied": now()
            },
            {
                "id": 2,
                "app": "test1",
                "name": "test1",
                "applied": now()
            }
        ]

        migrations = MigrationBackup().get_migrations_data_from_backup()

        self.assertEqual(migrations[0].id, 1)
        self.assertEqual(migrations[0].app, "test")
        self.assertEqual(migrations[0].name, "test")

        self.assertEqual(migrations[1].id, 2)
        self.assertEqual(migrations[1].app, "test1")
        self.assertEqual(migrations[1].name, "test1")
