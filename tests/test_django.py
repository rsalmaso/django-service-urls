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
import unittest

import django

import django_service_urls.loads  # noqa: F401

os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"
django.setup()


class MonkeyPatchDjangoTestCase(unittest.TestCase):
    def test_databases(self):
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

    def test_caches(self):
        from django.conf import settings

        CACHES = settings.CACHES
        default_cache = CACHES["default"]
        self.assertTrue(isinstance(default_cache, dict))
        self.assertEqual(default_cache["BACKEND"], "django.core.cache.backends.locmem.LocMemCache")

    def test_email(self):
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
