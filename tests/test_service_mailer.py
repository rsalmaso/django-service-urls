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

import unittest

from django_service_urls import mailer, ValidationError

SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Each entry: (tuple of equivalent urls, expected OPTIONS dict)
MAILER_SMTP_DEFAULT_TESTS = [
    (("smtp://", "smtp://:@:"), {"host": "localhost"}),
    (("smtps://", "smtps://:@:"), {"host": "localhost", "use_tls": True}),
    (("smtp+tls://", "smtp+tls://:@:"), {"host": "localhost", "use_tls": True}),
    (("smtp+ssl://", "smtp+ssl://:@:"), {"host": "localhost", "use_ssl": True}),
]


class MailerSmtpTests(unittest.TestCase):
    def test_parsing_python_backend_should_raise_an_exception(self) -> None:
        self.assertRaises(ValidationError, mailer.parse, SMTP_BACKEND)

    def test_default_values(self) -> None:
        for urls, expected in MAILER_SMTP_DEFAULT_TESTS:
            for url in urls:
                with self.subTest(url=f"Testing {url!r}"):
                    result = mailer.parse(url)
                    self.assertEqual(result["BACKEND"], SMTP_BACKEND)
                    self.assertEqual(result["OPTIONS"], expected)

    def test_smtp_sparse_options(self) -> None:
        """Only values present in the URL end up in OPTIONS (besides the required host)."""
        result = mailer.parse("smtp://user:pass@smtp.example.net")
        self.assertEqual(result["BACKEND"], SMTP_BACKEND)
        self.assertEqual(
            result["OPTIONS"],
            {"host": "smtp.example.net", "username": "user", "password": "pass"},
        )

    def test_smtp_with_all_ssl_options(self) -> None:
        result = mailer.parse(
            "smtp://user:pass@host:587/?use_tls=true&use_ssl=false&ssl_certfile=/path/cert&ssl_keyfile=/path/key&timeout=60"
        )
        self.assertEqual(result["BACKEND"], SMTP_BACKEND)
        self.assertEqual(
            result["OPTIONS"],
            {
                "host": "host",
                "port": 587,
                "username": "user",
                "password": "pass",
                "use_tls": True,
                "use_ssl": False,
                "ssl_certfile": "/path/cert",
                "ssl_keyfile": "/path/key",
                "timeout": 60,
            },
        )

    def test_smtps_automatic_tls_setting(self) -> None:
        result = mailer.parse("smtps://user:pass@host:465/")
        self.assertEqual(result["OPTIONS"]["use_tls"], True)
        self.assertNotIn("use_ssl", result["OPTIONS"])

    def test_smtp_ssl_automatic_ssl_setting(self) -> None:
        result = mailer.parse("smtp+ssl://user:pass@host:465/")
        self.assertEqual(result["OPTIONS"]["use_ssl"], True)
        self.assertNotIn("use_tls", result["OPTIONS"])

    def test_unknown_query_params_pass_through(self) -> None:
        """Unrecognized query params are forwarded to OPTIONS."""
        result = mailer.parse("smtp://host/?custom_option=value")
        self.assertEqual(result["OPTIONS"]["custom_option"], "value")


class MailerConsoleTests(unittest.TestCase):
    def test_console(self) -> None:
        result = mailer.parse("console://")
        self.assertEqual(result["BACKEND"], "django.core.mail.backends.console.EmailBackend")
        self.assertNotIn("OPTIONS", result)


class MailerFileTests(unittest.TestCase):
    def test_file_empty(self) -> None:
        result = mailer.parse("file://")
        self.assertEqual(result["BACKEND"], "django.core.mail.backends.filebased.EmailBackend")
        self.assertEqual(result["OPTIONS"], {"file_path": "/"})

    def test_file_backend_windows_path(self) -> None:
        result = mailer.parse("file://C:/email/logs")
        self.assertEqual(result["OPTIONS"], {"file_path": "C:/email/logs"})

    def test_file_backend_unix_path(self) -> None:
        result = mailer.parse("file:///var/log/email")
        self.assertEqual(result["OPTIONS"], {"file_path": "/var/log/email"})


class MailerMemoryTests(unittest.TestCase):
    def test_memory(self) -> None:
        result = mailer.parse("memory://")
        self.assertEqual(result["BACKEND"], "django.core.mail.backends.locmem.EmailBackend")
        self.assertNotIn("OPTIONS", result)


class MailerDummyTests(unittest.TestCase):
    def test_dummy(self) -> None:
        result = mailer.parse("dummy://")
        self.assertEqual(result["BACKEND"], "django.core.mail.backends.dummy.EmailBackend")
        self.assertNotIn("OPTIONS", result)


class MailerDictTests(unittest.TestCase):
    def test_full_mailers_dict(self) -> None:
        result = mailer.parse(
            {
                "default": "smtp://user:pass@smtp.example.net?use_tls=true",
                "newsletters": {
                    "BACKEND": SMTP_BACKEND,
                    "OPTIONS": {"host": "bulk.example.com"},
                },
            }
        )
        self.assertEqual(
            result["default"],
            {
                "BACKEND": SMTP_BACKEND,
                "OPTIONS": {"host": "smtp.example.net", "username": "user", "password": "pass", "use_tls": True},
            },
        )
        # already-parsed dict entries pass through unchanged
        self.assertEqual(
            result["newsletters"],
            {"BACKEND": SMTP_BACKEND, "OPTIONS": {"host": "bulk.example.com"}},
        )


if __name__ == "__main__":
    unittest.main()
