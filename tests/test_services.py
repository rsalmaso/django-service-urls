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

from django_service_urls import Service


class MockTestService(Service):
    """Test service for registration tests."""

    def __init__(self):
        super().__init__()
        self.register(("test", "test.engine"))(self._test_callback)

    def _test_callback(self, backend, engine, scheme, url):
        parsed = backend.parse_url(url)
        return {"parsed": parsed["path"]}

    def config_from_url(self, engine, scheme, url):
        return {"engine": engine, "scheme": scheme}


class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.backend = Service()

    def test_an_empty_string_should_returns_an_empty_dict(self):
        class TestService(Service):
            def config_from_url(self, engine, scheme, url):
                return {}

        service = TestService()
        self.assertEqual(service.parse(""), {})

    def test_hostname_sensitivity(self):
        parsed = self.backend.parse_url("http://CaseSensitive")
        self.assertEqual(parsed["hostname"], "CaseSensitive")

    def test_port_is_an_integer(self):
        parsed = self.backend.parse_url("http://CaseSensitive:123")
        self.assertIsInstance(parsed["port"], int)

    def test_path_strips_leading_slash(self):
        parsed = self.backend.parse_url("http://test/abc")
        self.assertEqual(parsed["path"], "abc")

    def test_query_parameters_integer(self):
        parsed = self.backend.parse_url("http://test/?a=1")
        self.assertDictEqual(parsed["query"], {"a": 1})

    def test_query_parameters_boolean(self):
        parsed = self.backend.parse_url("http://test/?a=true&b=false&c=t&d=f&e=1&f=0&g=yes&h=no&i=y&j=n")
        self.assertDictEqual(
            parsed["query"],
            {
                "a": True,
                "b": False,
                "c": True,
                "d": False,
                "e": True,
                "f": False,
                "g": True,
                "h": False,
                "i": True,
                "j": False,
            },
        )

    def test_query_multiple_parameters(self):
        parsed = self.backend.parse_url("http://test/?a=one&a=two")
        self.assertDictEqual(parsed["query"], {"a": ["one", "two"]})

    def test_fragment_parameters(self):
        parsed = self.backend.parse_url(
            "dbengine://user:passwd@host:123/dbname?pool=true#KEY=42&ENABLED=true&TEST.default.NAME=testdb&TEST.default.ENABLED=true"
        )
        self.assertDictEqual(parsed["query"], {"pool": True})
        expected = {"KEY": 42, "ENABLED": True, "TEST": {"default": {"NAME": "testdb", "ENABLED": True}}}
        self.assertDictEqual(parsed["fragment"], expected)

    def test_does_not_reparse(self):
        parsed = self.backend.parse_url("http://test/abc")
        self.assertIs(self.backend.parse_url(parsed), parsed)

    def test_validate_with_valid_url(self):
        self.assertEqual(self.backend.validate("http://example.com"), "http")
        self.assertEqual(self.backend.validate("https://example.com"), "https")
        self.assertEqual(self.backend.validate("postgres://user:pass@host/db"), "postgres")
        self.assertEqual(self.backend.validate("mysql://user:pass@host/db"), "mysql")

    def test_validate_with_invalid_url(self):
        self.assertIsNone(self.backend.validate("not-a-url"))
        self.assertIsNone(self.backend.validate("missing-scheme"))
        self.assertIsNone(self.backend.validate(""))
        self.assertIsNone(self.backend.validate("://no-scheme"))

    def test_parse_with_empty_string(self):
        self.assertEqual(self.backend.parse(""), {})

    def test_parse_with_non_string(self):
        self.assertEqual(self.backend.parse(123), 123)
        self.assertEqual(self.backend.parse(None), None)
        self.assertEqual(self.backend.parse([1, 2, 3]), [1, 2, 3])

    def test_parse_with_invalid_url_raises_error(self):
        self.assertRaises(ValueError, self.backend.parse, "invalid-url")

    def test_parse_with_unregistered_scheme_raises_error(self):
        with self.assertRaises(ValueError) as cm:
            self.backend.parse("unknown://example.com")
        self.assertIn("unknown:// scheme not registered", str(cm.exception))

    def test_parse_with_dict_input(self):
        # Create a test service with a registered scheme
        backend = MockTestService()

        test_dict = {"key1": "test://host/value1", "key2": "test://host/value2", "key3": {"already": "parsed"}}

        result = backend.parse(test_dict)

        self.assertEqual(result["key1"], {"parsed": "value1"})
        self.assertEqual(result["key2"], {"parsed": "value2"})
        self.assertEqual(result["key3"], {"already": "parsed"})

    def test_register_decorator(self):
        @self.backend.register(("test", "test.engine"), ("test2", "test2.engine"))
        def test_callback(backend, engine, scheme, url):
            return {"engine": engine, "scheme": scheme}

        # Test that schemes are registered
        self.assertIn("test", self.backend._schemes)
        self.assertIn("test2", self.backend._schemes)

        # Test that callback and engine are stored correctly
        self.assertEqual(self.backend._schemes["test"]["callback"], test_callback)
        self.assertEqual(self.backend._schemes["test"]["engine"], "test.engine")
        self.assertEqual(self.backend._schemes["test2"]["callback"], test_callback)
        self.assertEqual(self.backend._schemes["test2"]["engine"], "test2.engine")

    def test_parse_url_with_multiple_netloc(self):
        url = "scheme://host1:1234,host2:5678/path"
        result = Service.parse_url(url, multiple_netloc=True)

        self.assertEqual(result["scheme"], "scheme")
        self.assertEqual(result["location"], ["host1:1234", "host2:5678"])
        self.assertIsNone(result["hostname"])
        self.assertIsNone(result["port"])

    def test_parse_url_without_multiple_netloc(self):
        url = "scheme://host:1234/path"
        result = Service.parse_url(url, multiple_netloc=False)

        self.assertEqual(result["scheme"], "scheme")
        self.assertEqual(result["location"], "host:1234")
        self.assertEqual(result["hostname"], "host")
        self.assertEqual(result["port"], 1234)

    def test_parse_url_with_dict_input(self):
        test_dict = {"key": "value"}
        result = Service.parse_url(test_dict)
        self.assertIs(result, test_dict)

    def test_parse_url_query_parameter_types(self):
        url = "scheme://host/path?int_param=123&bool_true=true&bool_false=false&string_param=value"
        result = Service.parse_url(url)

        self.assertEqual(result["query"]["int_param"], 123)
        self.assertEqual(result["query"]["bool_true"], True)
        self.assertEqual(result["query"]["bool_false"], False)
        self.assertEqual(result["query"]["string_param"], "value")

    def test_parse_url_path_handling(self):
        url = "scheme://host/some/path"
        result = Service.parse_url(url)

        self.assertEqual(result["path"], "some/path")  # Leading slash removed
        self.assertEqual(result["fullpath"], "/some/path")  # Full path preserved

    def test_parse_url_username_password_encoding(self):
        url = "scheme://user%40domain:pass%40word@host/db"
        result = Service.parse_url(url)

        # Note: urllib.parse.urlparse doesn't automatically decode username/password
        self.assertEqual(result["username"], "user%40domain")
        self.assertEqual(result["password"], "pass%40word")


if __name__ == "__main__":
    unittest.main()
