# Django Zero Migrations
As the project grows up, the number of migration files increases over time.
As a result, running them can consume a lot of time, specifically when you are running your tests.

`zeromigrations` is a command to reset migration files (**I SUGGEST NOT TO CALL IT ON PRODUCTION**).
It basically runs 4 command:

1. `migrate --fake {app_name} zero` for each app
2. Remove old migration files, As new migrations is going to be generated.
3. `makemigrations` to generate initial migration file.
4. `migrate --fake-initial` to fake generated initial files.

#### But besides that, this command can make a _backup_ to _restore_ in case of any failure.

**Note** that `migrate --fake` command only runs for your own apps and django apps like `contenttype` and third-party apps are excluded. 

## Installation
```shell
pip install django-zeromigrations
```

-----
## Usage
First, run the command:
```
python manage.py zeromigrations

I suggest to make a backups from both your migrations and django_migrations table (just in case).
1- make backup
2- restore last backup
3- just proceed
```
If you choose `1- make backup`, it would make a backup then zero migrations.

If you choose `2- restore last backup`, it tries to restore the latest backup that can be found. If not backup found,
it would raise an error.

If you choose `3- just proceed`, it assumes that you already have your own backup and start setting migrations zero.
