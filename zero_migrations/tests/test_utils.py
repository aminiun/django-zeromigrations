from datetime import datetime
from pathlib import Path
from shutil import rmtree
from unittest.mock import patch

from django.db.migrations.loader import MIGRATIONS_MODULE_NAME
from django.db.migrations.recorder import MigrationRecorder
from django.test import TestCase
from django.utils.timezone import now

from ..apps import ZeroMigrationsConfig
from ..exceptions import BackupError
from ..utils import BackupDir
from ..utils.backup import BackupFile, MigrationsTableBackup, MigrationFilesBackup, AppMigrationsDir
from ..utils.restore import MigrationsTableRestore


class TestBackupDir(TestCase):

    def setUp(self) -> None:
        self.test_backup_dir_name = "test"
        self.backup_dir = BackupDir(self.test_backup_dir_name)

    def test_path(self):
        self.assertEqual(
            str(self.backup_dir.path),
            str(Path(__file__).parent.parent / BackupDir.BACKUP_DIR_NAME / self.test_backup_dir_name)
        )

    @patch("zero_migrations.utils.os.listdir")
    def test_get_files_with_postfix(self, mock_listdir):
        mock_listdir.return_value = ["0001_sth.json", "0002_test.json"]

        files = self.backup_dir.get_files_with_postfix(postfix="test.json")
        self.assertEqual(files, ["0002_test.json"])


class TestAppMigrationsDir(TestCase):

    def setUp(self) -> None:
        self.test_app_name = ZeroMigrationsConfig.name
        self.migrations_dir = AppMigrationsDir(self.test_app_name)

    def test_path(self):
        self.assertEqual(
            str(self.migrations_dir.path),
            str(Path(__file__).parent.parent / MIGRATIONS_MODULE_NAME)
        )


class TestBackupFile(TestCase):

    def setUp(self) -> None:
        self.test_backup_dir_name = "test"

        self.backup_dir = BackupDir(self.test_backup_dir_name)
        self.backup_file = BackupFile(directory=self.backup_dir, file_name="test.json")

    @patch("zero_migrations.utils.os.listdir")
    def test_latest_revision_without_any_file_in_dir(self, mock_listdir):
        mock_listdir.return_value = []

        self.assertIsNone(self.backup_file.latest_revision)

    @patch("zero_migrations.utils.os.listdir")
    def test_latest_revision_with_files_in_dir(self, mock_listdir):
        mock_listdir.return_value = ["0001_test.json", "0002_test.json"]

        self.assertEqual(str(self.backup_file.latest_revision), "0002_test.json")

    @patch("zero_migrations.utils.os.listdir")
    def test_new_revision_without_any_file_in_dir(self, mock_listdir):
        mock_listdir.return_value = []

        self.assertEqual(str(self.backup_file.next_revision), f"{BackupFile.REVISION_START_FROM}_test.json")

    @patch("zero_migrations.utils.os.listdir")
    def test_new_revision_with_files_in_dir(self, mock_listdir):
        mock_listdir.return_value = ["0001_test.json", "0002_test.json"]

        self.assertEqual(str(self.backup_file.next_revision), "0003_test.json")

    @patch("zero_migrations.utils.os.listdir")
    def test_new_file_path_without_any_file_in_dir(self, mock_listdir):
        mock_listdir.return_value = []

        self.assertEqual(
            str(self.backup_file.new_file_path),
            str(self.backup_dir.path / f"{BackupFile.REVISION_START_FROM}_test.json")
        )

    @patch("zero_migrations.utils.os.listdir")
    def test_new_file_path_with_files_in_dir(self, mock_listdir):
        mock_listdir.return_value = ["0001_test.json", "0002_test.json"]

        self.assertEqual(
            str(self.backup_file.new_file_path),
            str(self.backup_dir.path / "0003_test.json")
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
        rmtree(self.backup_dir.path, ignore_errors=True)


class TestBackupMigrationsTable(TestCase):

    def setUp(self) -> None:
        self.backup_handler = MigrationsTableBackup()

    def test_get_migrations_data_from_db(self):
        migration_1 = MigrationRecorder.Migration.objects.create(app="test1", name="test1")
        migration_2 = MigrationRecorder.Migration.objects.create(app="test2", name="test2")

        migrations = self.backup_handler.get_migrations_data_from_db()

        self.assertEqual(migrations[0]["id"], migration_1.id)
        self.assertEqual(migrations[0]["app"], migration_1.app)
        self.assertEqual(migrations[0]["name"], migration_1.name)
        self.assertEqual(migrations[0]["applied"], migration_1.applied)

        self.assertEqual(migrations[1]["id"], migration_2.id)
        self.assertEqual(migrations[1]["app"], migration_2.app)
        self.assertEqual(migrations[1]["name"], migration_2.name)
        self.assertEqual(migrations[1]["applied"], migration_2.applied)

    @patch("zero_migrations.utils.backup.MigrationsTableBackup.get_migrations_data_from_db")
    def test_backup_with_invalid_backup_raise_error(self, mock_get_migration_data):
        mock_get_migration_data.return_value = [
            {
                "id": 1,
                "app": "test",
                "name": "test",
                "applied": now()
            }
        ]

        MigrationRecorder.Migration.objects.create(app="test1", name="test1")
        MigrationRecorder.Migration.objects.create(app="test2", name="test2")

        with self.assertRaises(BackupError):
            self.backup_handler.backup()


class TestRestoreMigrationsTable(TestCase):

    def setUp(self) -> None:
        self.restore_handler = MigrationsTableRestore()

    @patch("zero_migrations.utils.BackupFile.read")
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

        migrations = self.restore_handler.get_migrations_data_from_backup()

        self.assertEqual(migrations[0].id, 1)
        self.assertEqual(migrations[0].app, "test")
        self.assertEqual(migrations[0].name, "test")

        self.assertEqual(migrations[1].id, 2)
        self.assertEqual(migrations[1].app, "test1")
        self.assertEqual(migrations[1].name, "test1")

    @patch("zero_migrations.utils.BackupFile.read")
    def test_restore_data_from_backup_success(self, mock_read):
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

        self.restore_handler.restore()

        migrations = MigrationRecorder.Migration.objects.all()

        self.assertEqual(migrations.count(), 2)
        self.assertEqual(migrations[0].id, 1)
        self.assertEqual(migrations[0].app, "test")
        self.assertEqual(migrations[0].name, "test")

        self.assertEqual(migrations[1].id, 2)
        self.assertEqual(migrations[1].app, "test1")
        self.assertEqual(migrations[1].name, "test1")
