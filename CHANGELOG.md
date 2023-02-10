# Changelog

## [0.1.3] - 2023-02-10
### Fixed
- `long_description_content_type` in setup.cfg fixed.


## [0.1.2] - 2023-02-10
### Fixed
- Ignore third-party apps in the process.


## [0.1.1] - 2023-02-10
### Fixed
- Print an error when there is no backup in restoring process.


## [0.1.0] - 2023-02-10
### Added
- `django_migrations` table backup with revision.
- `django_migrations` table restore from last backup.
- Migration files backup from each installed app.
- Migration files restore from backup.
- `zeromigrations` command.
