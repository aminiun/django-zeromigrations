Django Zero Migrations (Reset Migrations)
======================

As the project grows up, the number of migration files increases over
time. As a result, running them can consume a lot of time, specifically
when you are running your tests.

``zeromigrations`` is a command to reset migration files. It basically runs 4 commands:

1. ``migrate --fake {app_name} zero`` for each app.
2. Remove old migration files, as new migrations is going to be
   generated.
3. ``makemigrations`` to generate initial migration file.
4. ``migrate --fake-initial`` to fake generated initial files.


**But besides that, this command can make a backup to restore in case of any failure.**

**Note** that ``migrate --fake`` command only runs for your own apps and
django apps like ``contenttype`` and third-party apps are excluded.

--------------

Installation
------------
First install the package:

.. code:: bash

    pip3 install django-zeromigrations

Then add it to your ``INSTALLED_APPS``:

.. code:: python

    INSTALLED_APPS = [
        ...
        "zero_migrations"
    ]

--------------

Usage
-----

First, run the command:

.. code::

    python manage.py zeromigrations

    I suggest to make a backups from both your migrations and django_migrations table (just in case).
    1- make backup
    2- restore last backup
    3- just proceed

If you choose ``1- make backup``, it would make a backup then zero
migrations.

If you choose ``2- restore last backup``, it tries to restore the latest
backup that can be found. If not backup found, it would raise an error.

If you choose ``3- just proceed``, it assumes that you already have your
own backup and start setting migrations zero.
