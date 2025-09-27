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

from django_service_urls import email, ValidationError

EMAIL_SMTP_DEFAULT_TESTS = [
    (
        ("smtp://", "smtp://:@:"),
        {
            "HOST": "localhost",
            "PORT": 25,
            "HOST_USER": "",
            "HOST_PASSWORD": "",
            "USE_TLS": False,
            "USE_SSL": False,
            "SSL_CERTFILE": None,
            "SSL_KEYFILE": None,
            "TIMEOUT": None,
            "USE_LOCALTIME": False,
        },
    ),
    (
        ("smtps://", "smtps://:@:"),
        {
            "HOST": "localhost",
            "PORT": 25,
            "HOST_USER": "",
            "HOST_PASSWORD": "",
            "USE_TLS": True,
            "USE_SSL": False,
            "SSL_CERTFILE": None,
            "SSL_KEYFILE": None,
            "TIMEOUT": None,
        },
    ),
    (
        ("smtp+tls://", "smtp+tls://:@:"),
        {
            "HOST": "localhost",
            "PORT": 25,
            "HOST_USER": "",
            "HOST_PASSWORD": "",
            "USE_TLS": True,
            "USE_SSL": False,
            "SSL_CERTFILE": None,
            "SSL_KEYFILE": None,
            "TIMEOUT": None,
        },
    ),
    (
        ("smtp+ssl://", "smtp+ssl://:@:"),
        {
            "HOST": "localhost",
            "PORT": 25,
            "HOST_USER": "",
            "HOST_PASSWORD": "",
            "USE_TLS": False,
            "USE_SSL": True,
            "SSL_CERTFILE": None,
            "SSL_KEYFILE": None,
            "TIMEOUT": None,
        },
    ),
]


class EmailsTests(unittest.TestCase):
    def test_parsing_python_email_backend_should_raise_an_exception(self) -> None:
        self.assertRaises(ValidationError, email.parse, "django.core.mail.backends.console.EmailBackend")

    def test_default_values(self) -> None:
        for test in EMAIL_SMTP_DEFAULT_TESTS:
            urls, expected = test[0], test[1]
            for url in urls:
                with self.subTest(url=f"Testing {url!r}"):
                    result = email.parse(url)
                    self.assertEqual(result["ENGINE"], "django.core.mail.backends.smtp.EmailBackend")
                    for k, v in expected.items():
                        self.assertEqual(result[k], v)

    def test_smtp_with_all_ssl_options(self) -> None:
        """Test SMTP with all SSL options."""
        result = email.parse(
            "smtp://user:pass@host:587/?use_tls=true&use_ssl=false&ssl_certfile=/path/cert&ssl_keyfile=/path/key&timeout=60"
        )
        self.assertEqual(result["ENGINE"], "django.core.mail.backends.smtp.EmailBackend")
        self.assertEqual(result["HOST"], "host")
        self.assertEqual(result["PORT"], 587)
        self.assertEqual(result["HOST_USER"], "user")
        self.assertEqual(result["HOST_PASSWORD"], "pass")
        self.assertEqual(result["USE_TLS"], True)
        self.assertEqual(result["USE_SSL"], False)
        self.assertEqual(result["SSL_CERTFILE"], "/path/cert")
        self.assertEqual(result["SSL_KEYFILE"], "/path/key")
        self.assertEqual(result["TIMEOUT"], 60)

    def test_smtp_with_use_localtime_option(self) -> None:
        """Test SMTP with use_localtime option."""
        result = email.parse("smtp://user:pass@host:587/?use_localtime=true")
        self.assertEqual(result["USE_LOCALTIME"], True)

    def test_smtps_automatic_tls_setting(self) -> None:
        """Test that smtps:// automatically sets USE_TLS=True."""
        result = email.parse("smtps://user:pass@host:465/")
        self.assertEqual(result["USE_TLS"], True)
        self.assertEqual(result["USE_SSL"], False)

    def test_smtp_tls_automatic_tls_setting(self) -> None:
        """Test that smtp+tls:// automatically sets USE_TLS=True."""
        result = email.parse("smtp+tls://user:pass@host:587/")
        self.assertEqual(result["USE_TLS"], True)
        self.assertEqual(result["USE_SSL"], False)

    def test_smtp_ssl_automatic_ssl_setting(self) -> None:
        """Test that smtp+ssl:// automatically sets USE_SSL=True."""
        result = email.parse("smtp+ssl://user:pass@host:465/")
        self.assertEqual(result["USE_TLS"], False)
        self.assertEqual(result["USE_SSL"], True)


class ConsoleEmailTestCase(unittest.TestCase):
    def test_console(self) -> None:
        result = email.parse("console://")
        self.assertEqual(result["ENGINE"], "django.core.mail.backends.console.EmailBackend")


class FileEmailTestCase(unittest.TestCase):
    def test_file_empty(self) -> None:
        result = email.parse("file://")
        self.assertEqual(result["ENGINE"], "django.core.mail.backends.filebased.EmailBackend")
        self.assertEqual(result["FILE_PATH"], "/")

    def test_file_backend_windows_path(self) -> None:
        result = email.parse("file://C:/email/logs")
        self.assertEqual(result["ENGINE"], "django.core.mail.backends.filebased.EmailBackend")
        self.assertEqual(result["FILE_PATH"], "C:/email/logs")

    def test_file_backend_unix_path(self) -> None:
        result = email.parse("file:///var/log/email")
        self.assertEqual(result["ENGINE"], "django.core.mail.backends.filebased.EmailBackend")
        self.assertEqual(result["FILE_PATH"], "/var/log/email")


class MemoryEmailTestCase(unittest.TestCase):
    def test_memory(self) -> None:
        result = email.parse("memory://")
        self.assertEqual(result["ENGINE"], "django.core.mail.backends.locmem.EmailBackend")


class DummyEmailTestCase(unittest.TestCase):
    def test_dummy(self) -> None:
        result = email.parse("dummy://")
        self.assertEqual(result["ENGINE"], "django.core.mail.backends.dummy.EmailBackend")


if __name__ == "__main__":
    unittest.main()
