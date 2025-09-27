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

from typing import Any
import unittest

from django_service_urls.base import ConfigDict, Service
from django_service_urls.parse import parse_url, UrlInfo


class MockTestService(Service):
    """Test service for registration tests."""

    def __init__(self) -> None:
        super().__init__()
        self.register(("test", "test.engine"))(self._test_callback)

    def _test_callback(
        self, backend: Service, engine: str, scheme: str, url: str | UrlInfo, **kwargs: Any
    ) -> ConfigDict:
        parsed = backend.parse_url(url)
        return {"parsed": parsed.path}

    def config_from_url(self, engine: str, scheme: str, url: str | UrlInfo, **kwargs: Any) -> ConfigDict:
        return {"engine": engine, "scheme": scheme}


class ServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = Service()

    def test_an_empty_string_should_returns_an_empty_dict(self) -> None:
        class TestService(Service):
            def config_from_url(self, engine: str, scheme: str, url: str | UrlInfo, **kwargs: Any) -> ConfigDict:
                return {}

        service = TestService()
        self.assertEqual(service.parse(""), {})

    def test_validate_with_valid_url(self) -> None:
        self.assertEqual(self.backend.validate("http://example.com"), "http")
        self.assertEqual(self.backend.validate("https://example.com"), "https")
        self.assertEqual(self.backend.validate("postgres://user:pass@host/db"), "postgres")
        self.assertEqual(self.backend.validate("mysql://user:pass@host/db"), "mysql")

    def test_validate_with_invalid_url(self) -> None:
        self.assertIsNone(self.backend.validate("not-a-url"))
        self.assertIsNone(self.backend.validate("missing-scheme"))
        self.assertIsNone(self.backend.validate(""))
        self.assertIsNone(self.backend.validate("://no-scheme"))

    def test_parse_with_empty_string(self) -> None:
        self.assertEqual(self.backend.parse(""), {})

    def test_parse_with_invalid_types_raises_error(self) -> None:
        self.assertRaises(ValueError, self.backend.parse, 123)
        self.assertRaises(ValueError, self.backend.parse, None)
        self.assertRaises(ValueError, self.backend.parse, [1, 2, 3])

    def test_parse_with_invalid_url_raises_error(self) -> None:
        self.assertRaises(ValueError, self.backend.parse, "invalid-url")

    def test_parse_with_unregistered_scheme_raises_error(self) -> None:
        self.assertRaises(ValueError, self.backend.parse, "unknown://example.com")

    def test_parse_with_dict_input(self) -> None:
        # Create a test service with a registered scheme
        backend = MockTestService()

        test_dict = {"key1": "test://host/value1", "key2": "test://host/value2", "key3": {"already": "parsed"}}

        result = backend.parse(test_dict)

        self.assertEqual(result["key1"], {"parsed": "value1"})
        self.assertEqual(result["key2"], {"parsed": "value2"})
        self.assertEqual(result["key3"], {"already": "parsed"})

    def test_register_decorator(self) -> None:
        @self.backend.register(("test", "test.engine"), ("test2", "test2.engine"))
        def test_callback(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
            return {"engine": engine, "scheme": scheme}

        # Test that schemes are registered
        self.assertIn("test", self.backend._schemes)
        self.assertIn("test2", self.backend._schemes)

        # Test that callback and engine are stored correctly
        self.assertEqual(self.backend._schemes["test"]["callback"], test_callback)
        self.assertEqual(self.backend._schemes["test"]["engine"], "test.engine")
        self.assertEqual(self.backend._schemes["test2"]["callback"], test_callback)
        self.assertEqual(self.backend._schemes["test2"]["engine"], "test2.engine")

    def test_parse_url_path_handling(self) -> None:
        url = "scheme://host/some/path"
        result = parse_url(url)

        self.assertEqual(result.path, "some/path")  # Leading slash removed
        self.assertEqual(result.fullpath, "/some/path")  # Full path preserved

    def test_parse_url_username_password_encoding(self) -> None:
        url = "scheme://user%40domain:pass%40word@host/db"
        result = parse_url(url)

        # Note: urllib.parse.urlsplit doesn't automatically decode username/password
        self.assertEqual(result.username, "user%40domain")
        self.assertEqual(result.password, "pass%40word")


if __name__ == "__main__":
    unittest.main()
