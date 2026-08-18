# Copyright (C) Raffaele Salmaso <raffaele@salmaso.org>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
# THE POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import types
from typing import cast
import unittest

import django
from django.conf import Settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend

import django_service_urls.loads  # noqa: F401

MAILERS_SUPPORTED = django.VERSION >= (6, 1)
EMAIL_SETTINGS_SUPPORTED = django.VERSION < (7, 0)

SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
_EMAIL_URL = "smtps://myuser:mypasswd@smtpserver:42/?ssl_certfile=mycert&timeout=30"

os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"
django.setup()


def build_settings(name: str, **settings: object) -> Settings:
    """
    Build an isolated ``Settings`` object from an in-memory settings module.

    This exercises django-service-urls' patched ``Settings.__init__`` (URL parsing
    and version guards) followed by Django's own initialization, without disturbing
    the process-wide settings configured by ``django.setup()``.
    """

    module = types.ModuleType(name)
    module.SECRET_KEY = "test"  # type: ignore[attr-defined]
    for key, value in settings.items():
        setattr(module, key, value)
    sys.modules[name] = module
    try:
        return Settings(name)
    finally:
        del sys.modules[name]


class MonkeyPatchDjangoTestCase(unittest.TestCase):
    def test_databases(self) -> None:
        from django.conf import settings

        DATABASES = settings.DATABASES
        default_database = DATABASES["default"]
        self.assertTrue(isinstance(default_database, dict))
        self.assertEqual(default_database["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(default_database["NAME"], "mydb")
        analytics_database = DATABASES["analytics"]
        self.assertTrue(isinstance(analytics_database, dict))
        self.assertEqual(analytics_database["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(analytics_database["NAME"], "/tmp/analytics.db")

    def test_caches(self) -> None:
        from django.conf import settings

        CACHES = settings.CACHES
        default_cache = CACHES["default"]
        self.assertTrue(isinstance(default_cache, dict))
        self.assertEqual(default_cache["BACKEND"], "django.core.cache.backends.locmem.LocMemCache")

    @unittest.skipUnless(EMAIL_SETTINGS_SUPPORTED, "EMAIL_* settings are removed in Django 7.0")
    def test_email(self) -> None:
        from django.conf import settings

        self.assertEqual(settings.EMAIL_BACKEND, "django.core.mail.backends.smtp.EmailBackend")
        self.assertEqual(settings.EMAIL_HOST, "smtpserver")
        self.assertEqual(settings.EMAIL_PORT, 42)
        self.assertEqual(settings.EMAIL_HOST_USER, "myuser")
        self.assertEqual(settings.EMAIL_HOST_PASSWORD, "mypasswd")
        self.assertEqual(settings.EMAIL_USE_TLS, True)
        self.assertEqual(settings.EMAIL_USE_SSL, False)
        self.assertEqual(settings.EMAIL_SSL_CERTFILE, "mycert")
        self.assertEqual(settings.EMAIL_SSL_KEYFILE, None)
        self.assertEqual(settings.EMAIL_TIMEOUT, 30)

    def test_storages(self) -> None:
        from django.conf import settings

        STORAGES = settings.STORAGES
        default_storage = STORAGES["default"]
        self.assertTrue(isinstance(default_storage, dict))
        self.assertEqual(default_storage["BACKEND"], "django.core.files.storage.filesystem.FileSystemStorage")
        staticfiles_storage = STORAGES["staticfiles"]
        self.assertTrue(isinstance(staticfiles_storage, dict))
        self.assertEqual(staticfiles_storage["BACKEND"], "django.contrib.staticfiles.storage.StaticFilesStorage")

    def test_tasks(self) -> None:
        from django.conf import settings

        TASKS = settings.TASKS
        default_task = TASKS["default"]
        self.assertTrue(isinstance(default_task, dict))
        self.assertEqual(default_task["BACKEND"], "django.tasks.backends.immediate.ImmediateBackend")

    def test_ensure_that_locale_keep_the_right_path(self) -> None:
        import datetime as dt

        from django.template import engines
        from django.utils import translation

        engine = engines.all()[0]
        template = engine.from_string("{{ now }}")

        with translation.override("en"):
            output = template.render(context={"now": dt.date(2025, 3, 21)})
            self.assertEqual(output, "March 21, 2025")
        with translation.override("it"):
            output = template.render(context={"now": dt.date(2025, 3, 21)})
            self.assertEqual(output, "21 Marzo 2025")


class EmailBackendVersionTests(unittest.TestCase):
    """EMAIL_BACKEND service URL behaviour across Django versions."""

    @unittest.skipUnless(django.VERSION < (6, 1), "targets Django < 6.1")
    def test_works_before_6_1(self) -> None:
        # EMAIL_BACKEND is expanded into the EMAIL_* settings, as it always has been.
        values = vars(build_settings("svc_email_pre61", EMAIL_BACKEND=_EMAIL_URL))
        self.assertEqual(values["EMAIL_BACKEND"], SMTP_BACKEND)
        self.assertEqual(values["EMAIL_HOST"], "smtpserver")
        self.assertEqual(values["EMAIL_PORT"], 42)

    @unittest.skipUnless((6, 1) <= django.VERSION < (7, 0), "targets Django 6.1 .. <7.0")
    def test_works_and_warns_on_6_1(self) -> None:
        # Still works, but Django emits its own deprecation warning. We rely on
        # Django's RemovedInDjango70Warning and deliberately do not add our own.
        from django.utils.deprecation import RemovedInDjango70Warning

        with self.assertWarns(RemovedInDjango70Warning):
            values = vars(build_settings("svc_email_61", EMAIL_BACKEND=_EMAIL_URL))
        self.assertEqual(values["EMAIL_BACKEND"], SMTP_BACKEND)
        self.assertEqual(values["EMAIL_HOST"], "smtpserver")

    @unittest.skipUnless(django.VERSION >= (7, 0), "targets Django >= 7.0")
    def test_url_raises_on_7_0(self) -> None:
        # EMAIL_* is removed in Django 7.0: a service URL must raise instead of
        # being silently dropped. (Our own guard, in addition to Django's.)
        with self.assertRaises(ImproperlyConfigured):
            build_settings("svc_email_70", EMAIL_BACKEND=_EMAIL_URL)


class MailersVersionTests(unittest.TestCase):
    """MAILERS service URL behaviour across Django versions."""

    @unittest.skipIf(MAILERS_SUPPORTED, "targets Django < 6.1")
    def test_raises_before_6_1(self) -> None:
        # MAILERS is unknown before Django 6.1, so it must raise rather than be
        # silently ignored.
        with self.assertRaises(ImproperlyConfigured):
            build_settings("svc_mailers_pre61", MAILERS={"default": _EMAIL_URL})

    @unittest.skipUnless(MAILERS_SUPPORTED, "MAILERS requires Django 6.1+")
    def test_options_are_accepted_by_the_backend(self) -> None:
        # The OPTIONS we emit must match the backend's real signature, so build an
        # actual mailer from them and check the values landed where they belong.
        from django.core import mail
        from django.test import override_settings

        from django_service_urls import mailer

        with override_settings(MAILERS=mailer.parse({"default": _EMAIL_URL})):
            connection = mail.mailers["default"]
        # mailers[alias] is typed as the base backend; these options live on the SMTP one.
        self.assertIsInstance(connection, SMTPEmailBackend)
        backend = cast("SMTPEmailBackend", connection)
        self.assertEqual(backend.host, "smtpserver")
        self.assertEqual(backend.port, 42)
        self.assertEqual(backend.username, "myuser")
        self.assertEqual(backend.password, "mypasswd")
        self.assertEqual(backend.use_tls, True)
        self.assertEqual(backend.timeout, 30)

    @unittest.skipUnless(MAILERS_SUPPORTED, "MAILERS requires Django 6.1+")
    def test_unmappable_option_is_rejected_by_the_backend(self) -> None:
        # use_localtime has no per-mailer equivalent. Forwarding it (rather than
        # dropping it) is what makes the backend reject the config loudly instead
        # of quietly ignoring what the URL asked for.
        from django.core import mail
        from django.core.mail import InvalidMailer
        from django.test import override_settings

        from django_service_urls import mailer

        config = mailer.parse({"default": "smtp://user:pass@host:587/?use_localtime=true"})
        with override_settings(MAILERS=config), self.assertRaises(InvalidMailer):
            mail.mailers["default"]

    @unittest.skipUnless(MAILERS_SUPPORTED, "MAILERS requires Django 6.1+")
    def test_both_email_backend_and_mailers_raises(self) -> None:
        # Django itself forbids mixing the deprecated EMAIL_* settings with MAILERS
        # (Settings._check_email_settings_conflicts). We rely on that check rather
        # than adding our own.
        with self.assertRaises(ImproperlyConfigured):
            build_settings("svc_both", EMAIL_BACKEND=_EMAIL_URL, MAILERS={"default": _EMAIL_URL})

    @unittest.skipUnless(MAILERS_SUPPORTED, "MAILERS requires Django 6.1+")
    def test_parsed_on_6_1(self) -> None:
        values = vars(build_settings("svc_mailers_61", MAILERS={"default": _EMAIL_URL}))
        self.assertEqual(
            values["MAILERS"]["default"],
            {
                "BACKEND": SMTP_BACKEND,
                "OPTIONS": {
                    "host": "smtpserver",
                    "port": 42,
                    "username": "myuser",
                    "password": "mypasswd",
                    "use_tls": True,
                    "ssl_certfile": "mycert",
                    "timeout": 30,
                },
            },
        )
