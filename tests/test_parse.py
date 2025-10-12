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

import unittest

from django_service_urls.parse import _get_host_and_port, parse_url, UrlInfo


class GetHostAndPortTestCase(unittest.TestCase):
    """Test get_host_and_port utility function."""

    def test_get_host_and_port(self) -> None:
        test_cases = [
            # (input, expected_hostname, expected_port, description)
            # Test basic hostname and port parsing.
            ("localhost", "localhost", None, "hostname only"),
            ("localhost:5432", "localhost", 5432, "hostname with port"),
            ("db.example.com:3306", "db.example.com", 3306, "domain with port"),
            ("192.168.1.1:8080", "192.168.1.1", 8080, "IPv4 with port"),
            ("192.168.1.1", "192.168.1.1", None, "IPv4 only"),
            # Test netloc parsing with authentication credentials.
            ("user@localhost", "localhost", None, "username only"),
            ("user:pass@localhost", "localhost", None, "username and password"),
            ("user@localhost:5432", "localhost", 5432, "username with port"),
            ("user:pass@localhost:5432", "localhost", 5432, "username, password, and port"),
            ("user:pass@db.example.com:3306", "db.example.com", 3306, "credentials with domain and port"),
            ("user@[::1]:5432", "::1", 5432, "username with IPv6 and port"),
            ("user:pass@[2001:db8::1]:443", "2001:db8::1", 443, "credentials with IPv6 and port"),
            # Test edge cases and special scenarios.
            ("localhost:0", "localhost", 0, "port zero"),
            ("localhost:65535", "localhost", 65535, "max port number"),
            ("subdomain.domain.tld:8080", "subdomain.domain.tld", 8080, "multi-level domain"),
            ("hyphen-host:3000", "hyphen-host", 3000, "hostname with hyphens"),
            ("_service._tcp.example.com:53", "_service._tcp.example.com", 53, "service record hostname"),
            ("user:complex@pass@host:1234", "host", 1234, "complex password with @ symbol"),
            # Test IPv6 address parsing.
            ("[::1]", "::1", None, "IPv6 localhost without port"),
            ("[::1]:5432", "::1", 5432, "IPv6 localhost with port"),
            ("[2001:db8::1]", "2001:db8::1", None, "IPv6 address without port"),
            ("[2001:db8::1]:443", "2001:db8::1", 443, "IPv6 address with port"),
            ("[fe80::1%eth0]:8080", "fe80::1%eth0", 8080, "IPv6 with zone ID and port"),
        ]

        for netloc, expected_hostname, expected_port, description in test_cases:
            with self.subTest(netloc=netloc, description=description):
                hostname, port = _get_host_and_port(netloc)
                self.assertEqual(hostname, expected_hostname)
                self.assertEqual(port, expected_port)


class ParseUrlTestCase(unittest.TestCase):
    def test_hostname_preserve_case_sensitivity(self) -> None:
        parsed = parse_url("http://CaseSensitive")
        self.assertEqual(parsed.hostname, "CaseSensitive")

    def test_hostname_is_url_encoded(self) -> None:
        parsed = parse_url("http://Host%2DName.Example%2ECom:8080/path")

        self.assertEqual(parsed.hostname, "Host-Name.Example.Com")
        self.assertEqual(parsed.port, 8080)

    def test_hostname_is_url_encoded_with_special_chars(self) -> None:
        parsed = parse_url("http://my%2Dserver%2Ename:3306/db")

        self.assertEqual(parsed.hostname, "my-server.name")
        self.assertEqual(parsed.port, 3306)

    def test_port_is_an_integer(self) -> None:
        parsed = parse_url("http://CaseSensitive:123")
        self.assertIsInstance(parsed.port, int)

    def test_path_strips_leading_slash(self) -> None:
        parsed = parse_url("http://test/abc/def")
        self.assertEqual(parsed.path, "abc/def")

    def test_query_parameters_integer(self) -> None:
        parsed = parse_url("http://test/?a=1")
        self.assertDictEqual(parsed.query, {"a": 1})

    def test_query_parameters_boolean(self) -> None:
        parsed = parse_url("http://test/?a=true&b=false&c=t&d=f&e=1&f=0&g=yes&h=no&i=y&j=n")
        self.assertDictEqual(
            parsed.query,
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

    def test_query_multiple_parameters(self) -> None:
        parsed = parse_url("http://test/?a=one&a=two")
        self.assertDictEqual(parsed.query, {"a": ["one", "two"]})

    def test_fragment_parameters(self) -> None:
        parsed = parse_url(
            "dbengine://user:passwd@host:123/dbname?pool=true#KEY=42&ENABLED=true&TEST.default.NAME=testdb&TEST.default.ENABLED=true"
        )
        self.assertDictEqual(parsed.query, {"pool": True})
        expected = {"KEY": 42, "ENABLED": True, "TEST": {"default": {"NAME": "testdb", "ENABLED": True}}}
        self.assertDictEqual(parsed.fragment, expected)

    def test_does_not_reparse(self) -> None:
        parsed = parse_url("http://test/abc")
        self.assertIs(parse_url(parsed), parsed)

    def test_parse_url_with_multiple_netloc(self) -> None:
        url = "scheme://host1:1234,host2:5678/path"
        result = parse_url(url, multiple_netloc=True)

        self.assertEqual(result.scheme, "scheme")
        self.assertEqual(result.location, ["host1:1234", "host2:5678"])
        self.assertIsNone(result.hostname)
        self.assertIsNone(result.port)

    def test_parse_url_without_multiple_netloc(self) -> None:
        url = "scheme://host:1234/path"
        result = parse_url(url, multiple_netloc=False)

        self.assertEqual(result.scheme, "scheme")
        self.assertEqual(result.location, "host:1234")
        self.assertEqual(result.hostname, "host")
        self.assertEqual(result.port, 1234)

    def test_parse_url_with_already_parsed_url(self) -> None:
        input = UrlInfo()
        result = parse_url(input)
        self.assertIs(result, input)

    def test_parse_url_query_parameter_types(self) -> None:
        url = "scheme://host/path?int_param=123&bool_true=true&bool_false=false&string_param=value"
        result = parse_url(url)

        self.assertEqual(result.query["int_param"], 123)
        self.assertEqual(result.query["bool_true"], True)
        self.assertEqual(result.query["bool_false"], False)
        self.assertEqual(result.query["string_param"], "value")

    def test_parse_url_path_handling(self) -> None:
        url = "scheme://host/some/path"
        result = parse_url(url)

        self.assertEqual(result.path, "some/path")  # Leading slash removed
        self.assertEqual(result.fullpath, "/some/path")  # Full path preserved

    def test_parse_url_with_encoded_path(self) -> None:
        url = "scheme://host/My%20Database/Test%2DDB"
        result = parse_url(url)

        self.assertEqual(result.path, "My Database/Test-DB")
        self.assertEqual(result.fullpath, "/My Database/Test-DB")

    def test_parse_url_path_with_special_chars(self) -> None:
        url = "scheme://host/path%2Fwith%2Fslashes/name%40domain/file%23123.db"
        result = parse_url(url)

        self.assertEqual(result.path, "path/with/slashes/name@domain/file#123.db")
        self.assertEqual(result.fullpath, "/path/with/slashes/name@domain/file#123.db")

    def test_parse_url_preserve_case_sensitivity(self) -> None:
        url = "scheme://host/MyDatabase/TestDB/CamelCase%20Path"
        result = parse_url(url)

        self.assertEqual(result.path, "MyDatabase/TestDB/CamelCase Path")
        self.assertEqual(result.fullpath, "/MyDatabase/TestDB/CamelCase Path")

    def test_parse_url_path_windows_style(self) -> None:
        url = "scheme://host/C%3A/Users/MyApp/database.db"
        result = parse_url(url)

        self.assertEqual(result.path, "C:/Users/MyApp/database.db")
        self.assertEqual(result.fullpath, "/C:/Users/MyApp/database.db")

    def test_parse_url_username_and_password_encoding(self) -> None:
        url = "scheme://user%40domain:pass%40word@host/db"
        result = parse_url(url)

        self.assertEqual(result.username, "user@domain")
        self.assertEqual(result.password, "pass@word")

    def test_parse_url_username_and_password_with_special_chars(self) -> None:
        url = "scheme://user%2Fname:p%40ss%23word%20123@host/db"
        result = parse_url(url)

        self.assertEqual(result.username, "user/name")
        self.assertEqual(result.password, "p@ss#word 123")


if __name__ == "__main__":
    unittest.main()
