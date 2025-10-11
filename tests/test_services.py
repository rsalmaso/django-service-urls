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
from django_service_urls.exceptions import ValidationError
from django_service_urls.parse import UrlInfo


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
        self.assertEqual(self.backend.parse(""), {})

    def test_parse_with_invalid_types_raises_error(self) -> None:
        self.assertRaises(ValidationError, self.backend.parse, 123)
        self.assertRaises(ValidationError, self.backend.parse, None)
        self.assertRaises(ValidationError, self.backend.parse, [1, 2, 3])

    def test_parse_an_invalid_url_and_require_a_valid_uri_raises_an_error(self) -> None:
        self.assertRaises(ValidationError, self.backend.parse, "invalid-url")

    def test_parse_with_unregistered_scheme_raises_an_error(self) -> None:
        with self.assertRaises(ValidationError) as cm:
            self.backend.parse("invalid://nonexistent")

        error = cm.exception
        self.assertIsInstance(error, ValidationError)
        self.assertTrue(hasattr(error, "message"))
        self.assertIn("invalid://", str(error))

    def test_parse_with_dict_input(self) -> None:
        backend = MockTestService()

        test_dict = {
            "key1": "test://host/value1",
            "key2": "test://host/value2",
            "key3": {"already": "parsed"},
        }

        result = backend.parse(test_dict)

        self.assertEqual(
            result,
            {
                "key1": {"parsed": "value1"},
                "key2": {"parsed": "value2"},
                "key3": {"already": "parsed"},
            },
        )

    def test_parse_django_setting_with_errors(self) -> None:
        test_data = {
            "db1": "invalid://scheme1",
            "db2": "not_a_uri_string",
        }

        with self.assertRaises(ValidationError) as cm:
            self.backend.parse(test_data)

        error = cm.exception
        self.assertIsInstance(error, ValidationError)
        self.assertTrue(hasattr(error, "error_dict"))

        error_dict = error.error_dict
        self.assertIn("db1", error_dict)
        self.assertIn("db2", error_dict)
        self.assertEqual(len(error_dict), 2)

        self.assertIn("scheme is not registered", error_dict["db1"])
        self.assertIn("invalid", error_dict["db2"])

    def test_register_decorator(self) -> None:
        @self.backend.register(("test", "test.engine"), ("test2", "test2.engine"))
        def test_callback(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
            return {"engine": engine, "scheme": scheme}

        # Test that schemes are registered
        self.assertIn("test", self.backend._schemes)
        self.assertIn("test2", self.backend._schemes)

        # Test that callback and engine are stored correctly
        self.assertEqual(self.backend._schemes["test"], {"callback": test_callback, "engine": "test.engine"})
        self.assertEqual(self.backend._schemes["test2"], {"callback": test_callback, "engine": "test2.engine"})

    def test_mixed_url_and_backend_string_pattern(self) -> None:
        """Test the pattern for handling both URLs and backend path strings."""
        backend = MockTestService()

        # Test with valid URL - should parse successfully
        url_string = "test://host/mypath"
        result: ConfigDict | str | None
        try:
            result = backend.parse(url_string)
            parsed_successfully = True
        except ValidationError:
            parsed_successfully = False
            result = None

        self.assertTrue(parsed_successfully)
        self.assertEqual(result, {"parsed": "mypath"})

        # Test with backend path string - should raise ValidationError
        backend_path = "my.backend.BackendClass"
        try:
            result = backend.parse(backend_path)
            parsed_successfully = True
        except ValidationError:
            parsed_successfully = False
            result = backend_path  # Use the original string as fallback

        self.assertFalse(parsed_successfully)
        self.assertEqual(result, "my.backend.BackendClass")


if __name__ == "__main__":
    unittest.main()
