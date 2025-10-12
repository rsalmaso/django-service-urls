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
    STRING_PORTS = False  # Workaround for Oracle and MSSQL

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

    def test_url_encoded_username_and_password(self) -> None:
        if self.SCHEME is None:
            return
        # Test @ symbol and # symbol which are special in URLs
        result = db.parse(f"{self.SCHEME}://user%40domain:p%40ss%23word@host:5432/dbname")
        self.assertEqual(result["USER"], "user@domain")  # type: ignore[attr-defined]
        self.assertEqual(result["PASSWORD"], "p@ss#word")  # type: ignore[attr-defined]

    def test_url_encoded_complex_username_and_password(self) -> None:
        if self.SCHEME is None:
            return
        # Test slash, space, and other special characters
        result = db.parse(f"{self.SCHEME}://my%2Fuser:pass%20word%21%40%23%24@host:5432/database")
        self.assertEqual(result["USER"], "my/user")  # type: ignore[attr-defined]
        self.assertEqual(result["PASSWORD"], "pass word!@#$")  # type: ignore[attr-defined]
        self.assertEqual(result["HOST"], "host")  # type: ignore[attr-defined]
        self.assertEqual(result["NAME"], "database")  # type: ignore[attr-defined]

    def test_url_encoded_hostname(self) -> None:
        if self.SCHEME is None:
            return
        # Test hostname with encoded special characters and mixed case
        result = db.parse(f"{self.SCHEME}://user:pass@My%2DServer%2EExample%2ECom:5432/database")
        self.assertEqual(result["HOST"], "My-Server.Example.Com")  # type: ignore[attr-defined]
        self.assertEqual(result["USER"], "user")  # type: ignore[attr-defined]
        self.assertEqual(result["NAME"], "database")  # type: ignore[attr-defined]

    def test_url_encoded_database_name(self) -> None:
        if self.SCHEME is None:
            return
        # Test database name with spaces and special characters
        result = db.parse(f"{self.SCHEME}://user:pass@host:5432/My%20Database%2DName")
        self.assertEqual(result["NAME"], "My Database-Name")  # type: ignore[attr-defined]
        self.assertEqual(result["HOST"], "host")  # type: ignore[attr-defined]

    def test_url_encoded_complex_database_path(self) -> None:
        if self.SCHEME is None:
            return
        # Test path with @, #, and other special chars
        result = db.parse(f"{self.SCHEME}://user:pass@host:5432/path%2Fto%2Fdb%40company%23123")
        self.assertEqual(result["NAME"], "path/to/db@company#123")  # type: ignore[attr-defined]
        self.assertEqual(result["USER"], "user")  # type: ignore[attr-defined]


class SqliteTests(unittest.TestCase):
    def test_empty_url(self) -> None:
        result = db.parse("sqlite://")
        self.assertEqual(result["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(result["NAME"], ":memory:")

    def test_memory_url(self) -> None:
        result = db.parse("sqlite://:memory:")
        self.assertEqual(result["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(result["NAME"], ":memory:")

    def _test_file(self, dbname: str, expected: str | None = None) -> None:
        result = db.parse(f"sqlite://{dbname}")
        self.assertEqual(result["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(result["NAME"], dbname if expected is None else expected)
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

    def test_url_encoded_path(self) -> None:
        self._test_file("/My%20Database%20File.db", "/My Database File.db")

    def test_url_encoded_path_with_spaces_and_special_chars(self) -> None:
        self._test_file("/path%2Fto%2Fmy%20db%40company%23123.db", "/path/to/my db@company#123.db")

    def test_url_encoded_windows_path(self) -> None:
        # Note: SQLite URLs with three slashes have the leading slash preserved
        self._test_file("/C%3A/Users/My%20User/AppData/database.db", "/C:/Users/My User/AppData/database.db")

    def test_case_sensitive_path(self) -> None:
        self._test_file("/MyDatabase/TestDB/CamelCaseFile.db", "/MyDatabase/TestDB/CamelCaseFile.db")

    def test_spatialite_file_database(self) -> None:
        result = db.parse("spatialite:///path/to/spatial.db")
        self.assertEqual(result["ENGINE"], "django.contrib.gis.db.backends.spatialite")
        self.assertEqual(result["NAME"], "/path/to/spatial.db")

    def test_pragma_with_fragment(self) -> None:
        result = db.parse(
            "sqlite:///path/to/db.sqlite3#PRAGMA.journal_mode=WAL&PRAGMA.synchronous=NORMAL&CONN_MAX_AGE=300"
        )
        init_command = result["OPTIONS"]["init_command"]
        self.assertEqual(result["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(result["NAME"], "/path/to/db.sqlite3")
        self.assertIn("PRAGMA journal_mode=WAL;", init_command)
        self.assertIn("PRAGMA synchronous=NORMAL;", init_command)
        self.assertEqual(result["CONN_MAX_AGE"], 300)
        # Verify PRAGMA is not in top-level config
        self.assertNotIn("PRAGMA", result)

    def test_spatialite_with_pragma(self) -> None:
        result = db.parse("spatialite:///path/to/spatial.db#PRAGMA.journal_mode=WAL")
        self.assertEqual(result["ENGINE"], "django.contrib.gis.db.backends.spatialite")
        self.assertEqual(result["NAME"], "/path/to/spatial.db")
        self.assertEqual(result["OPTIONS"]["init_command"], "PRAGMA journal_mode=WAL;")


class SqlitePlusTests(unittest.TestCase):
    def test_file_database_with_production_defaults(self) -> None:
        result = db.parse("sqlite+:///path/to/db.sqlite3")
        self.assertEqual(result["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(result["NAME"], "/path/to/db.sqlite3")
        self.assertEqual(result["OPTIONS"]["transaction_mode"], "IMMEDIATE")
        self.assertEqual(result["OPTIONS"]["timeout"], 5)
        self.assertIn("PRAGMA journal_mode=WAL", result["OPTIONS"]["init_command"])
        self.assertIn("PRAGMA synchronous=NORMAL", result["OPTIONS"]["init_command"])
        self.assertIn("PRAGMA temp_store=MEMORY", result["OPTIONS"]["init_command"])

    def test_override_defaults(self) -> None:
        result = db.parse(
            "sqlite+:///path/to/db.sqlite3#PRAGMA.journal_mode=DELETE&PRAGMA.synchronous=FULL&CONN_MAX_AGE=300"
        )
        self.assertEqual(result["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(result["NAME"], "/path/to/db.sqlite3")
        init_command = result["OPTIONS"]["init_command"]
        self.assertIn("PRAGMA journal_mode=DELETE;", init_command)
        self.assertIn("PRAGMA synchronous=FULL;", init_command)
        self.assertNotIn("PRAGMA journal_mode=WAL;", init_command)
        self.assertNotIn("PRAGMA synchronous=NORMAL;", init_command)
        self.assertEqual(result["CONN_MAX_AGE"], 300)
        # Other defaults should still be present
        self.assertIn("PRAGMA temp_store=MEMORY", result["OPTIONS"]["init_command"])

    def test_windows_path(self) -> None:
        result = db.parse("sqlite+:///C:/Users/data/db.sqlite3")
        # Note: SQLite URLs with three slashes have the leading slash preserved
        self.assertEqual(result["NAME"], "/C:/Users/data/db.sqlite3")
        self.assertEqual(result["OPTIONS"]["transaction_mode"], "IMMEDIATE")


class PostgresTests(DatabaseTestCaseMixin, unittest.TestCase):
    SCHEME = "postgres"

    def test_empty_data(self) -> None:
        for url in ["postgres://", "postgres://:@:/"]:
            with self.subTest(url=url):
                result = db.parse(url)
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
        SERVICES = [
            ("mysql", "django.db.backends.mysql"),
            ("mysql+gis", "django.contrib.gis.db.backends.mysql"),
            ("mysqlgis", "django.contrib.gis.db.backends.mysql"),
        ]
        for scheme, engine in SERVICES:
            for url in [f"{scheme}://", f"{scheme}://:@:/"]:
                with self.subTest(url=url):
                    result = db.parse(url)
                    self.assertEqual(result["ENGINE"], engine)
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
        SERVICES = [
            ("oracle", "django.db.backends.oracle"),
            ("oracle+gis", "django.contrib.gis.db.backends.oracle"),
            ("oraclegis", "django.contrib.gis.db.backends.oracle"),
        ]
        for scheme, engine in SERVICES:
            for url in [f"{scheme}://", f"{scheme}://:@:/"]:
                with self.subTest(url=url):
                    result = db.parse(url)
                    self.assertEqual(result["ENGINE"], engine)
                    self.assertEqual(result["NAME"], "")
                    self.assertEqual(result["HOST"], "")
                    self.assertEqual(result["USER"], "")
                    self.assertEqual(result["PASSWORD"], "")
                    self.assertEqual(result["PORT"], "")

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


class MSSQLTests(DatabaseTestCaseMixin, unittest.TestCase):
    SCHEME = "mssql"
    STRING_PORTS = True

    def test_empty_data(self) -> None:
        SERVICES = [
            ("mssql", "sql_server.pyodbc"),
            ("mssqlms", "mssql"),
        ]
        for scheme, engine in SERVICES:
            for url in [f"{scheme}://", f"{scheme}://:@:/"]:
                with self.subTest(url=url):
                    result = db.parse(url)
                    self.assertEqual(result["ENGINE"], engine)
                    self.assertEqual(result["NAME"], "")
                    self.assertEqual(result["HOST"], "")
                    self.assertEqual(result["USER"], "")
                    self.assertEqual(result["PASSWORD"], "")
                    self.assertEqual(result["PORT"], "")

    def test_mssql_port_string_conversion(self) -> None:
        result = db.parse("mssql://user:pass@host:1433/dbname")
        self.assertIsInstance(result["PORT"], str)
        self.assertEqual(result["PORT"], "1433")

    def test_mssqlms_backend(self) -> None:
        result = db.parse("mssqlms://user:pass@host:1433/dbname")
        self.assertEqual(result["ENGINE"], "mssql")
        self.assertEqual(result["NAME"], "dbname")
        self.assertEqual(result["PORT"], "1433")

    def test_mssql_with_options(self) -> None:
        result = db.parse("mssql://user:password@host:1433/database?driver=ODBC+Driver+17+for+SQL+Server")
        self.assertEqual(result["ENGINE"], "sql_server.pyodbc")
        self.assertEqual(result["OPTIONS"]["driver"], "ODBC Driver 17 for SQL Server")

    def test_multiple_nested_groups(self) -> None:
        result = db.parse(
            f"{self.SCHEME}://user:passwd@host:1433/dbname?driver=ODBC+Driver+17"
            "&connection.pool.min_size=4&connection.pool.max_size=10"
            "&connection.pool.enabled=true"
            "#CONN_MAX_AGE=42&TEST.default.NAME=testdb"
        )
        expected_options = {
            "driver": "ODBC Driver 17",
            "connection": {
                "pool": {
                    "min_size": 4,
                    "max_size": 10,
                    "enabled": True,
                },
            },
        }
        self.assertEqual(result["ENGINE"], "sql_server.pyodbc")
        self.assertEqual(result["NAME"], "dbname")
        self.assertEqual(result["USER"], "user")
        self.assertEqual(result["PASSWORD"], "passwd")
        self.assertEqual(result["HOST"], "host")
        self.assertEqual(result["PORT"], "1433")
        self.assertEqual(result["OPTIONS"], expected_options)
        self.assertEqual(result["CONN_MAX_AGE"], 42)
        self.assertEqual(result["TEST"], {"default": {"NAME": "testdb"}})


class RedshiftTests(DatabaseTestCaseMixin, unittest.TestCase):
    SCHEME = "redshift"

    def test_empty_data(self) -> None:
        for url in ["redshift://", "redshift://:@:/"]:
            with self.subTest(url=url):
                result = db.parse(url)
                self.assertEqual(result["ENGINE"], "django_redshift_backend")
                self.assertEqual(result["NAME"], "")
                self.assertEqual(result["HOST"], "")
                self.assertEqual(result["USER"], "")
                self.assertEqual(result["PASSWORD"], "")
                self.assertEqual(result["PORT"], "")

    def test_redshift_parsing(self) -> None:
        result = db.parse("redshift://user:pass@host:5439/dbname?currentSchema=myschema")
        self.assertEqual(result["ENGINE"], "django_redshift_backend")
        self.assertEqual(result["NAME"], "dbname")
        self.assertEqual(result["USER"], "user")
        self.assertEqual(result["PASSWORD"], "pass")
        self.assertEqual(result["HOST"], "host")
        self.assertEqual(result["PORT"], 5439)
        self.assertEqual(result["OPTIONS"]["options"], "-c search_path=myschema")
        self.assertNotIn("currentSchema", result["OPTIONS"])


class CockroachDBTests(DatabaseTestCaseMixin, unittest.TestCase):
    SCHEME = "cockroach"

    def test_empty_data(self) -> None:
        for url in ["cockroach://", "cockroach://:@:/"]:
            with self.subTest(url=url):
                result = db.parse(url)
                self.assertEqual(result["ENGINE"], "django_cockroachdb")
                self.assertEqual(result["NAME"], "")
                self.assertEqual(result["HOST"], "")
                self.assertEqual(result["USER"], "")
                self.assertEqual(result["PASSWORD"], "")
                self.assertEqual(result["PORT"], "")

    def test_cockroach_parsing(self) -> None:
        result = db.parse("cockroach://user:pass@host:26257/dbname?sslmode=require&sslrootcert=/path/to/cert")
        self.assertEqual(result["ENGINE"], "django_cockroachdb")
        self.assertEqual(result["NAME"], "dbname")
        self.assertEqual(result["USER"], "user")
        self.assertEqual(result["PASSWORD"], "pass")
        self.assertEqual(result["HOST"], "host")
        self.assertEqual(result["PORT"], 26257)
        self.assertEqual(result["OPTIONS"]["sslmode"], "require")
        self.assertEqual(result["OPTIONS"]["sslrootcert"], "/path/to/cert")


class TimescaleTests(DatabaseTestCaseMixin, unittest.TestCase):
    SCHEME = "timescale"

    def test_empty_data(self) -> None:
        SERVICES = [
            ("timescale", "timescale.db.backends.postgresql"),
            ("timescale+gis", "timescale.db.backend.postgis"),
            ("timescalegis", "timescale.db.backend.postgis"),
        ]
        for scheme, engine in SERVICES:
            for url in [f"{scheme}://", f"{scheme}://:@:/"]:
                with self.subTest(url=url):
                    result = db.parse(url)
                    self.assertEqual(result["ENGINE"], engine)
                    self.assertEqual(result["NAME"], "")
                    self.assertEqual(result["HOST"], "")
                    self.assertEqual(result["USER"], "")
                    self.assertEqual(result["PASSWORD"], "")
                    self.assertEqual(result["PORT"], "")

    def test_timescale_parsing(self) -> None:
        result = db.parse("timescale://user:pass@host:5432/dbname")
        self.assertEqual(result["ENGINE"], "timescale.db.backends.postgresql")
        self.assertEqual(result["NAME"], "dbname")
        self.assertEqual(result["USER"], "user")
        self.assertEqual(result["PASSWORD"], "pass")
        self.assertEqual(result["HOST"], "host")
        self.assertEqual(result["PORT"], 5432)

    def test_timescale_gis_backend(self) -> None:
        result = db.parse("timescale+gis://user:pass@host:5432/dbname")
        self.assertEqual(result["ENGINE"], "timescale.db.backend.postgis")
        self.assertEqual(result["NAME"], "dbname")

    def test_timescalegis_alias(self) -> None:
        result = db.parse("timescalegis://user:pass@host:5432/dbname")
        self.assertEqual(result["ENGINE"], "timescale.db.backend.postgis")
        self.assertEqual(result["NAME"], "dbname")

    def test_timescale_with_current_schema(self) -> None:
        result = db.parse("timescale://user:pass@host:5432/dbname?currentSchema=timeseries")
        self.assertEqual(result["ENGINE"], "timescale.db.backends.postgresql")
        self.assertEqual(result["OPTIONS"]["options"], "-c search_path=timeseries")
        self.assertNotIn("currentSchema", result["OPTIONS"])

    def test_timescale_unix_socket_parsing(self) -> None:
        result = db.parse("timescale://%2Fvar%2Frun%2Fpostgresql/dbname")
        self.assertEqual(result["ENGINE"], "timescale.db.backends.postgresql")
        self.assertEqual(result["NAME"], "dbname")
        self.assertEqual(result["HOST"], "/var/run/postgresql")


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
