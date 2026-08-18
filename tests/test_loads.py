# Copyright (C) Raffaele Salmaso <raffaele@salmaso.org>
# Copyright (C) Tom Forbes
# Copyright (C) Kenneth Reitz
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

import types
import unittest
from unittest.mock import patch

import django
from django.conf import global_settings
from django.core.exceptions import ImproperlyConfigured

from django_service_urls.loads import apply_service_urls, email_settings_supported, mailers_supported

SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


def make_settings(**attrs: object) -> types.ModuleType:
    module = types.ModuleType("fake_settings")
    for name, value in attrs.items():
        setattr(module, name, value)
    return module


class SupportDetectionTests(unittest.TestCase):
    def test_email_settings_supported_reflects_global_settings(self) -> None:
        self.assertEqual(email_settings_supported(), hasattr(global_settings, "EMAIL_BACKEND"))
        # Every currently-supported Django version still ships the EMAIL_* settings.
        self.assertTrue(email_settings_supported())

    def test_email_settings_not_supported_when_removed(self) -> None:
        # Simulate Django 7.0, where the deprecated EMAIL_* settings are removed.
        original = global_settings.EMAIL_BACKEND
        del global_settings.EMAIL_BACKEND
        try:
            self.assertFalse(email_settings_supported())
        finally:
            global_settings.EMAIL_BACKEND = original

    def test_mailers_supported_matches_version(self) -> None:
        self.assertEqual(mailers_supported(), django.VERSION >= (6, 1))


class ApplyMailersTests(unittest.TestCase):
    def test_raises_when_mailers_unsupported(self) -> None:
        module = make_settings(MAILERS={"default": "smtp://host"})
        with (
            patch("django_service_urls.loads.mailers_supported", return_value=False),
            self.assertRaises(ImproperlyConfigured),
        ):
            apply_service_urls(module)

    def test_parses_when_mailers_supported(self) -> None:
        module = make_settings(MAILERS={"default": "smtp://user:pass@host?use_tls=true"})
        with patch("django_service_urls.loads.mailers_supported", return_value=True):
            apply_service_urls(module)
        self.assertEqual(
            vars(module)["MAILERS"]["default"],
            {
                "BACKEND": SMTP_BACKEND,
                "OPTIONS": {"host": "host", "username": "user", "password": "pass", "use_tls": True},
            },
        )


class ApplyEmailBackendTests(unittest.TestCase):
    def test_url_raises_when_email_settings_unsupported(self) -> None:
        module = make_settings(EMAIL_BACKEND="smtp://host")
        with (
            patch("django_service_urls.loads.email_settings_supported", return_value=False),
            self.assertRaises(ImproperlyConfigured),
        ):
            apply_service_urls(module)

    def test_plain_backend_path_ignored_when_unsupported(self) -> None:
        # A plain backend import path is not a service URL, so it is left untouched
        # and must not raise even when EMAIL_* is unsupported.
        module = make_settings(EMAIL_BACKEND=SMTP_BACKEND)
        with patch("django_service_urls.loads.email_settings_supported", return_value=False):
            apply_service_urls(module)
        self.assertEqual(vars(module)["EMAIL_BACKEND"], SMTP_BACKEND)

    def test_url_expanded_when_supported(self) -> None:
        module = make_settings(EMAIL_BACKEND="smtps://user:pass@host:42/?timeout=30")
        with patch("django_service_urls.loads.email_settings_supported", return_value=True):
            apply_service_urls(module)
        settings = vars(module)
        self.assertEqual(settings["EMAIL_BACKEND"], SMTP_BACKEND)
        self.assertEqual(settings["EMAIL_HOST"], "host")
        self.assertEqual(settings["EMAIL_PORT"], 42)
        self.assertEqual(settings["EMAIL_USE_TLS"], True)
        self.assertEqual(settings["EMAIL_TIMEOUT"], 30)


if __name__ == "__main__":
    unittest.main()
