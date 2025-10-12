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

from django_service_urls import cache, db, ValidationError

GENERIC_TESTS = [
    ("username:password@domain/database", ("username", "password", "domain", "", "database", {})),
    ("username:password@domain:123/database", ("username", "password", "domain", 123, "database", {})),
    ("domain:123/database", ("", "", "domain", 123, "database", {})),
    ("user@domain:123/database", ("user", "", "domain", 123, "database", {})),
    (
        "username:password@[2001:db8:1234::1234:5678:90af]:123/database",
        ("username", "password", "2001:db8:1234::1234:5678:90af", 123, "database", {}),
    ),
    (
        "username:password@host:123/database?reconnect=true",
        ("username", "password", "host", 123, "database", {"reconnect": True}),
    ),
    ("username:password@/database", ("username", "password", "", "", "database", {})),
]


class DatabaseTestCaseMixin:
    SCHEME: str | None = None
    STRING_PORTS = False  # Workaround for Oracle

    def test_parsing(self) -> None:
        if self.SCHEME is None:
            return
        for value, (user, passw, host, port, database, options) in GENERIC_TESTS:
            value = f"{self.SCHEME}://{value}"
            with self.subTest(item=f"Parsing {value!r}"):  # type: ignore[attr-defined]
                result = db.parse(value)
                self.assertEqual(result["NAME"], database)  # type: ignore[attr-defined]
                self.assertEqual(result["HOST"], host)  # type: ignore[attr-defined]
                self.assertEqual(result["USER"], user)  # type: ignore[attr-defined]
                self.assertEqual(result["PASSWORD"], passw)  # type: ignore[attr-defined]
                self.assertEqual(result["PORT"], str(port) if self.STRING_PORTS else port)  # type: ignore[attr-defined]
                self.assertDictEqual(result["OPTIONS"], options)  # type: ignore[attr-defined]

    def test_multiple_nested_groups(self) -> None:
        result = db.parse(
            f"{self.SCHEME}://user:passwd@host:5432/dbname?sslmode=require"
            "&pool.min_size=4&pool.max_size=10"
            "&pool.enabled=true&pool.auto_reconnect=false&pool.strategy=round_robin"
            "&pool.health_check.query=SELECT%201"
            "&ssl.mode=require&ssl.cert=/path/to/cert&application_name=myapp"
            "#CONN_MAX_AGE=42&TEST.default.NAME=testdb"
        )
        expected_options = {
            "sslmode": "require",
            "application_name": "myapp",
            "pool": {
                "min_size": 4,
                "max_size": 10,
                "enabled": True,
                "auto_reconnect": False,
                "strategy": "round_robin",
                "health_check": {"query": "SELECT 1"},
            },
            "ssl": {"mode": "require", "cert": "/path/to/cert"},
        }
        self.assertIn(self.SCHEME, result["ENGINE"])  # type: ignore[attr-defined]
        self.assertEqual(result["NAME"], "dbname")  # type: ignore[attr-defined]
        self.assertEqual(result["USER"], "user")  # type: ignore[attr-defined]
        self.assertEqual(result["PASSWORD"], "passwd")  # type: ignore[attr-defined]
        self.assertEqual(result["HOST"], "host")  # type: ignore[attr-defined]
        self.assertEqual(result["PORT"], "5432" if self.STRING_PORTS else 5432)  # type: ignore[attr-defined]
        self.assertEqual(result["OPTIONS"], expected_options)  # type: ignore[attr-defined]
        self.assertEqual(result["CONN_MAX_AGE"], 42)  # type: ignore[attr-defined]
        self.assertEqual(result["TEST"], {"default": {"NAME": "testdb"}})  # type: ignore[attr-defined]

    def test_conflict_resolution_flat_to_nested(self) -> None:
        # This tests the conflict resolution where we have pool=something and pool.min_size=4
        # The nested structure should take precedence
        result = db.parse(f"{self.SCHEME}://user:pass@host:5432/dbname?pool=legacy&pool.min_size=4")
        expected_options = {"pool": {"min_size": 4}}

        self.assertEqual(result["OPTIONS"], expected_options)  # type: ignore[attr-defined]


class SqliteTests(unittest.TestCase):
    def test_empty_url(self) -> None:
        result = db.parse("sqlite://")
        self.assertEqual(result["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(result["NAME"], ":memory:")

    def test_memory_url(self) -> None:
        result = db.parse("sqlite://:memory:")
        self.assertEqual(result["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(result["NAME"], ":memory:")

    def _test_file(self, dbname: str) -> None:
        result = db.parse(f"sqlite://{dbname}")
        self.assertEqual(result["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(result["NAME"], dbname)
        self.assertEqual(result["HOST"], "")
        self.assertEqual(result["USER"], "")
        self.assertEqual(result["PASSWORD"], "")
        self.assertEqual(result["PORT"], "")
        self.assertDictEqual(result["OPTIONS"], {})

    def test_unix_path_with_absolute_path(self) -> None:
        self._test_file("/home/user/projects/project/app.sqlite3")

    def test_unix_path_with_relative_path(self) -> None:
        self.assertRaises(AssertionError, self._test_file, "app.sqlite3")

    def test_windows_path_with_drive_letter_and_subdirs(self) -> None:
        self._test_file("C:/home/user/projects/project/app.sqlite3")

    def test_spatialite_file_database(self) -> None:
        result = db.parse("spatialite:///path/to/spatial.db")
        self.assertEqual(result["ENGINE"], "django.contrib.gis.db.backends.spatialite")
        self.assertEqual(result["NAME"], "/path/to/spatial.db")


class PostgresTests(DatabaseTestCaseMixin, unittest.TestCase):
    SCHEME = "postgres"

    def test_empty_data(self) -> None:
        result = db.parse("postgres://:@:/")
        self.assertEqual(result["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(result["NAME"], "")
        self.assertEqual(result["HOST"], "")
        self.assertEqual(result["USER"], "")
        self.assertEqual(result["PASSWORD"], "")
        self.assertEqual(result["PORT"], "")

    def test_network_parsing(self) -> None:
        result = db.parse("postgres://user:@:5435/database")
        self.assertEqual(result["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(result["NAME"], "database")
        self.assertEqual(result["HOST"], "")
        self.assertEqual(result["USER"], "user")
        self.assertEqual(result["PASSWORD"], "")
        self.assertEqual(result["PORT"], 5435)

    def test_unix_socket_parsing(self) -> None:
        result = db.parse("postgres://%2Fvar%2Frun%2Fpostgresql/database")
        self.assertEqual(result["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(result["NAME"], "database")
        self.assertEqual(result["HOST"], "/var/run/postgresql")
        self.assertEqual(result["USER"], "")
        self.assertEqual(result["PASSWORD"], "")
        self.assertEqual(result["PORT"], "")

        result = db.parse("postgres://C%3A%2Fvar%2Frun%2Fpostgresql/database")
        self.assertEqual(result["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(result["HOST"], "C:/var/run/postgresql")
        self.assertEqual(result["USER"], "")
        self.assertEqual(result["PASSWORD"], "")
        self.assertEqual(result["PORT"], "")

    def test_search_path_schema_parsing(self) -> None:
        result = db.parse("postgres://user:password@host:5431/database?currentSchema=otherschema")
        self.assertEqual(result["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(result["NAME"], "database")
        self.assertEqual(result["HOST"], "host")
        self.assertEqual(result["USER"], "user")
        self.assertEqual(result["PASSWORD"], "password")
        self.assertEqual(result["PORT"], 5431)
        self.assertEqual(result["OPTIONS"]["options"], "-c search_path=otherschema")
        self.assertNotIn("currentSchema", result["OPTIONS"])

    def test_parsing_with_special_characters(self) -> None:
        result = db.parse("postgres://%23user:%23password@host:5431/%23database")
        self.assertEqual(result["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(result["NAME"], "#database")
        self.assertEqual(result["HOST"], "host")
        self.assertEqual(result["USER"], "#user")
        self.assertEqual(result["PASSWORD"], "#password")
        self.assertEqual(result["PORT"], 5431)

    def test_database_url_with_options(self) -> None:
        result = db.parse(
            "postgres://user:password@host:5431/database?sslrootcert=rds-combined-ca-bundle.pem&sslmode=verify-full"
        )
        self.assertEqual(result["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(result["NAME"], "database")
        self.assertEqual(result["HOST"], "host")
        self.assertEqual(result["USER"], "user")
        self.assertEqual(result["PASSWORD"], "password")
        self.assertEqual(result["PORT"], 5431)
        self.assertEqual(result["OPTIONS"], {"sslrootcert": "rds-combined-ca-bundle.pem", "sslmode": "verify-full"})

    def test_gis_search_path_parsing(self) -> None:
        result = db.parse("postgis://user:password@host:5431/database?currentSchema=otherschema")
        self.assertEqual(result["ENGINE"], "django.contrib.gis.db.backends.postgis")
        self.assertEqual(result["NAME"], "database")
        self.assertEqual(result["HOST"], "host")
        self.assertEqual(result["USER"], "user")
        self.assertEqual(result["PASSWORD"], "password")
        self.assertEqual(result["PORT"], 5431)
        self.assertEqual(result["OPTIONS"]["options"], "-c search_path=otherschema")
        self.assertNotIn("currentSchema", result["OPTIONS"])

    def test_postgres_compatibility_aliases(self) -> None:
        for alias in ["postgresql", "pgsql"]:
            with self.subTest(alias=alias):
                result = db.parse(f"{alias}://user:pass@host:5432/dbname")
                self.assertEqual(result["ENGINE"], "django.db.backends.postgresql")
                self.assertEqual(result["NAME"], "dbname")
                self.assertEqual(result["HOST"], "host")
                self.assertEqual(result["USER"], "user")
                self.assertEqual(result["PASSWORD"], "pass")
                self.assertEqual(result["PORT"], 5432)


class MysqlTests(DatabaseTestCaseMixin, unittest.TestCase):
    SCHEME = "mysql"

    def test_empty_data(self) -> None:
        result = db.parse("mysql://:@:/")
        self.assertEqual(result["ENGINE"], "django.db.backends.mysql")
        self.assertEqual(result["NAME"], "")
        self.assertEqual(result["HOST"], "")
        self.assertEqual(result["USER"], "")
        self.assertEqual(result["PASSWORD"], "")
        self.assertEqual(result["PORT"], "")

    def test_with_sslca_options(self) -> None:
        result = db.parse("mysql://user:password@host:3306/database?ssl-ca=rds-combined-ca-bundle.pem")
        self.assertEqual(result["ENGINE"], "django.db.backends.mysql")
        self.assertEqual(result["NAME"], "database")
        self.assertEqual(result["HOST"], "host")
        self.assertEqual(result["USER"], "user")
        self.assertEqual(result["PASSWORD"], "password")
        self.assertEqual(result["PORT"], 3306)
        self.assertEqual(result["OPTIONS"], {"ssl": {"ca": "rds-combined-ca-bundle.pem"}})

    def test_mysql_gis_backend(self) -> None:
        result = db.parse("mysql+gis://user:password@host:3306/database")
        self.assertEqual(result["ENGINE"], "django.contrib.gis.db.backends.mysql")
        self.assertEqual(result["NAME"], "database")

    def test_mysql_ssl_ca_option_handling(self) -> None:
        result = db.parse("mysql://user:password@host:3306/database?ssl-ca=/path/to/ca.pem")
        self.assertIn("ssl", result["OPTIONS"])
        self.assertEqual(result["OPTIONS"]["ssl"]["ca"], "/path/to/ca.pem")
        self.assertNotIn("ssl-ca", result["OPTIONS"])

    def test_mysqlgis_alias(self) -> None:
        result = db.parse("mysqlgis://user:password@host:3306/database")
        self.assertEqual(result["ENGINE"], "django.contrib.gis.db.backends.mysql")
        self.assertEqual(result["NAME"], "database")


class OracleTests(DatabaseTestCaseMixin, unittest.TestCase):
    SCHEME = "oracle"
    STRING_PORTS = True

    def test_empty_data(self) -> None:
        result = db.parse("oracle://:@:/")
        self.assertEqual(result["ENGINE"], "django.db.backends.oracle")
        self.assertEqual(result["NAME"], "")
        self.assertEqual(result["HOST"], "")
        self.assertEqual(result["USER"], "")
        self.assertEqual(result["PASSWORD"], "")

    def test_dsn_parsing(self) -> None:
        dsn = "(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=oraclehost)(PORT=1521)))(CONNECT_DATA=(SID=hr)))"
        result = db.parse("oracle://scott:tiger@/" + dsn)
        self.assertEqual(result["ENGINE"], "django.db.backends.oracle")
        self.assertEqual(result["USER"], "scott")
        self.assertEqual(result["PASSWORD"], "tiger")
        self.assertEqual(result["HOST"], "")
        self.assertEqual(result["PORT"], "")

    def test_empty_dsn_parsing(self) -> None:
        dsn = "(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=oraclehost)(PORT=1521)))(CONNECT_DATA=(SID=hr)))"
        self.assertRaises(ValidationError, db.parse, dsn)

    def test_oracle_gis_backend(self) -> None:
        result = db.parse("oracle+gis://user:pass@host:1521/dbname")
        self.assertEqual(result["ENGINE"], "django.contrib.gis.db.backends.oracle")
        self.assertEqual(result["NAME"], "dbname")
        self.assertEqual(result["PORT"], "1521")  # Oracle uses string ports

    def test_oracle_port_string_conversion(self) -> None:
        result = db.parse("oracle://user:pass@host:1521/dbname")
        self.assertIsInstance(result["PORT"], str)
        self.assertEqual(result["PORT"], "1521")

    def test_oraclegis_alias(self) -> None:
        result = db.parse("oraclegis://user:pass@host:1521/dbname")
        self.assertEqual(result["ENGINE"], "django.contrib.gis.db.backends.oracle")
        self.assertEqual(result["NAME"], "dbname")
        self.assertEqual(result["PORT"], "1521")


class DictionaryTests(unittest.TestCase):
    def test_databases(self) -> None:
        result = db.parse(
            {
                "default": "sqlite://:memory:",
                "postgresql": "postgres://user:@:5435/database",
                "mysql": {
                    "ENGINE": "django.db.backends.mysql",
                    "NAME": "database",
                    "HOST": "host",
                    "USER": "user",
                    "PASSWORD": "password",
                    "PORT": 3306,
                },
            }
        )
        self.assertEqual(result["default"]["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(result["default"]["NAME"], ":memory:")
        self.assertEqual(result["postgresql"]["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(result["postgresql"]["NAME"], "database")
        self.assertEqual(result["postgresql"]["HOST"], "")
        self.assertEqual(result["postgresql"]["USER"], "user")
        self.assertEqual(result["postgresql"]["PASSWORD"], "")
        self.assertEqual(result["postgresql"]["PORT"], 5435)
        self.assertEqual(result["mysql"]["ENGINE"], "django.db.backends.mysql")
        self.assertEqual(result["mysql"]["NAME"], "database")
        self.assertEqual(result["mysql"]["HOST"], "host")
        self.assertEqual(result["mysql"]["USER"], "user")
        self.assertEqual(result["mysql"]["PASSWORD"], "password")
        self.assertEqual(result["mysql"]["PORT"], 3306)

    def test_caches(self) -> None:
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

    def test_fragment_top_level_config(self) -> None:
        result = db.parse(
            "postgresql://user:pass@host:5432/dbname?pool=true#CONN_MAX_AGE=42&TEST.DATABASES.NAME=testdb"
        )

        self.assertEqual(result["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(result["NAME"], "dbname")
        self.assertEqual(result["CONN_MAX_AGE"], 42)
        self.assertEqual(result["OPTIONS"], {"pool": True})
        self.assertEqual(result["TEST"], {"DATABASES": {"NAME": "testdb"}})


if __name__ == "__main__":
    unittest.main()
