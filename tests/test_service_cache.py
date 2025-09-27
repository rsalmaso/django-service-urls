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

from django_service_urls import cache


class DictionaryTests(unittest.TestCase):
    def test_caches_as_dictionary(self) -> None:
        result = cache.parse(
            {
                "default": "memory://",
                "dummy": {
                    "BACKEND": "django.core.cache.backends.dummy.DummyCache",
                },
                "memcached": "memcached://1.2.3.4:1567,1.2.3.5:1568",
            }
        )
        self.assertEqual(result["default"]["BACKEND"], "django.core.cache.backends.locmem.LocMemCache")
        self.assertEqual(result["dummy"]["BACKEND"], "django.core.cache.backends.dummy.DummyCache")
        self.assertEqual(result["memcached"]["BACKEND"], "django.core.cache.backends.memcached.MemcachedCache")
        self.assertEqual(result["memcached"]["LOCATION"], ["1.2.3.4:1567", "1.2.3.5:1568"])


class CacheNestedOptionsTestCase(unittest.TestCase):
    def test_cache_nested_options(self) -> None:
        result = cache.parse(
            "pymemcached://host:11211/?binary_protocol.enabled=true&binary_protocol.version=2&timeout.connect=5&timeout.read=10"
        )
        expected_options = {"binary_protocol": {"enabled": True, "version": 2}, "timeout": {"connect": 5, "read": 10}}

        self.assertEqual(result["OPTIONS"], expected_options)


class MemoryCacheTestCase(unittest.TestCase):
    def test_local_caching_no_params(self) -> None:
        result = cache.parse("memory://")
        self.assertEqual(result["BACKEND"], "django.core.cache.backends.locmem.LocMemCache")
        self.assertNotIn("LOCATION", result)

    def test_local_caching_with_location(self) -> None:
        result = cache.parse("memory://location")
        self.assertEqual(result["BACKEND"], "django.core.cache.backends.locmem.LocMemCache")
        self.assertEqual(result["LOCATION"], "location")

    def test_cache_with_multiple_special_options(self) -> None:
        result = cache.parse("memory://location?timeout=300&key_prefix=app&version=1&custom=value")
        self.assertEqual(result["TIMEOUT"], 300)
        self.assertEqual(result["KEY_PREFIX"], "app")
        self.assertEqual(result["VERSION"], 1)
        self.assertEqual(result["OPTIONS"]["custom"], "value")


class DatabaseCacheTestCase(unittest.TestCase):
    def test_database_caching(self) -> None:
        result = cache.parse("db://table-name")
        self.assertEqual(result["BACKEND"], "django.core.cache.backends.db.DatabaseCache")
        self.assertEqual(result["LOCATION"], "table-name")


class DummyCacheTestCase(unittest.TestCase):
    def test_dummy_caching_no_params(self) -> None:
        result = cache.parse("dummy://")
        self.assertEqual(result["BACKEND"], "django.core.cache.backends.dummy.DummyCache")
        self.assertNotIn("LOCATION", result)

    def test_dummy_caching_with_location(self) -> None:
        result = cache.parse("dummy://abc")
        self.assertEqual(result["BACKEND"], "django.core.cache.backends.dummy.DummyCache")
        self.assertEqual(result["LOCATION"], "abc")


class PymemcachedCacheTestCase(unittest.TestCase):
    def test_pymemcached_with_host(self) -> None:
        for url, backend in [
            ("pymemcached://localhost:1567", "django.core.cache.backends.memcached.PyMemcachedCache"),
            ("memcached://localhost:1567", "django.core.cache.backends.memcached.MemcachedCache"),
        ]:
            with self.subTest(url=url):
                result = cache.parse(url)
                self.assertEqual(result["BACKEND"], backend)
                self.assertEqual(result["LOCATION"], "localhost:1567")

    def test_pymemcached_with_single_ip(self) -> None:
        for url, backend in [
            ("pymemcached://1.2.3.4:1567", "django.core.cache.backends.memcached.PyMemcachedCache"),
            ("memcached://1.2.3.4:1567", "django.core.cache.backends.memcached.MemcachedCache"),
        ]:
            with self.subTest(url=url):
                result = cache.parse(url)
                self.assertEqual(result["BACKEND"], backend)
                self.assertEqual(result["LOCATION"], "1.2.3.4:1567")

    def test_pymemcached_with_multiple_ips(self) -> None:
        for url, backend in [
            ("pymemcached://1.2.3.4:1567,1.2.3.5:1568", "django.core.cache.backends.memcached.PyMemcachedCache"),
            ("memcached://1.2.3.4:1567,1.2.3.5:1568", "django.core.cache.backends.memcached.MemcachedCache"),
        ]:
            with self.subTest(url=url):
                result = cache.parse(url)
                self.assertEqual(result["BACKEND"], backend)
                self.assertEqual(result["LOCATION"], ["1.2.3.4:1567", "1.2.3.5:1568"])

    def test_pymemcached_without_port(self) -> None:
        for url, backend in [
            ("pymemcached://1.2.3.4", "django.core.cache.backends.memcached.PyMemcachedCache"),
            ("memcached://1.2.3.4", "django.core.cache.backends.memcached.MemcachedCache"),
        ]:
            with self.subTest(url=url):
                result = cache.parse(url)
                self.assertEqual(result["BACKEND"], backend)
                self.assertEqual(result["LOCATION"], "1.2.3.4")

    def test_pymemcached_with_unix_socket(self) -> None:
        for url, backend in [
            ("pymemcached:///tmp/memcached.sock", "django.core.cache.backends.memcached.PyMemcachedCache"),
            ("memcached:///tmp/memcached.sock", "django.core.cache.backends.memcached.MemcachedCache"),
        ]:
            with self.subTest(url=url):
                result = cache.parse(url)
                self.assertEqual(result["BACKEND"], backend)
                self.assertEqual(result["LOCATION"], "unix:/tmp/memcached.sock")


class PylibmccacheCacheTestCase(unittest.TestCase):
    def test_pylibmccache_with_host(self) -> None:
        for url in [
            "pylibmccache://localhost:1567",
            "memcached+pylibmccache://localhost:1567",
        ]:
            with self.subTest(url=url):
                result = cache.parse(url)
                self.assertEqual(result["BACKEND"], "django.core.cache.backends.memcached.PyLibMCCache")
                self.assertEqual(result["LOCATION"], "localhost:1567")

    def test_pylibmccache_with_single_ip(self) -> None:
        for url in [
            "pylibmccache://1.2.3.4:1567",
            "memcached+pylibmccache://1.2.3.4:1567",
        ]:
            with self.subTest(url=url):
                result = cache.parse(url)
                self.assertEqual(result["BACKEND"], "django.core.cache.backends.memcached.PyLibMCCache")
                self.assertEqual(result["LOCATION"], "1.2.3.4:1567")

    def test_pylibmccache_with_multiple_ips(self) -> None:
        for url in [
            "pylibmccache://1.2.3.4:1567,1.2.3.5:1568",
            "memcached+pylibmccache://1.2.3.4:1567,1.2.3.5:1568",
        ]:
            with self.subTest(url=url):
                result = cache.parse(url)
                self.assertEqual(result["BACKEND"], "django.core.cache.backends.memcached.PyLibMCCache")
                self.assertEqual(result["LOCATION"], ["1.2.3.4:1567", "1.2.3.5:1568"])

    def test_pylibmccache_without_port(self) -> None:
        for url in [
            "pylibmccache://1.2.3.4",
            "memcached+pylibmccache://1.2.3.4",
        ]:
            with self.subTest(url=url):
                result = cache.parse(url)
                self.assertEqual(result["BACKEND"], "django.core.cache.backends.memcached.PyLibMCCache")
                self.assertEqual(result["LOCATION"], "1.2.3.4")

    def test_pylibmccache_with_unix_socket(self) -> None:
        for url in [
            "pylibmccache:///tmp/memcached.sock",
            "memcached+pylibmccache:///tmp/memcached.sock",
        ]:
            with self.subTest(url=url):
                result = cache.parse(url)
                self.assertEqual(result["BACKEND"], "django.core.cache.backends.memcached.PyLibMCCache")
                self.assertEqual(result["LOCATION"], "/tmp/memcached.sock")


class FileCacheTestCase(unittest.TestCase):
    def test_file_cache_windows_path(self) -> None:
        result = cache.parse("file://C:/abc/def/xyz")
        self.assertEqual(result["BACKEND"], "django.core.cache.backends.filebased.FileBasedCache")
        self.assertEqual(result["LOCATION"], "C:/abc/def/xyz")

    def test_file_cache_unix_path(self) -> None:
        result = cache.parse("file:///abc/def/xyz")
        self.assertEqual(result["BACKEND"], "django.core.cache.backends.filebased.FileBasedCache")
        self.assertEqual(result["LOCATION"], "/abc/def/xyz")


if __name__ == "__main__":
    unittest.main()
