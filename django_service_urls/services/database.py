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
from urllib import parse

from django_service_urls.base import ConfigDict, Service
from django_service_urls.parse import UrlInfo

__all__ = ["db"]


class DatabaseService(Service):
    def config_from_url(self, engine: str, scheme: str, url: str | UrlInfo, **kwargs: Any) -> ConfigDict:
        parsed: UrlInfo = self.parse_url(url)
        config: ConfigDict = {
            "ENGINE": engine,
            "NAME": parse.unquote(parsed.path or ""),
            "USER": parse.unquote(parsed.username or ""),
            "PASSWORD": parse.unquote(parsed.password or ""),
            "HOST": parsed.hostname,
            "PORT": parsed.port or "",
            "OPTIONS": parsed.query,
        }
        config.update({k: v for k, v in parsed.fragment.items() if k not in config})
        return config


db: DatabaseService = DatabaseService()


def _handle_postgres_like_config(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    parsed: UrlInfo = backend.parse_url(url)

    if parsed.hostname:
        host = parsed.hostname.lower()
        # Handle percent-encoded paths for Unix sockets
        if "%2f" in host or "%3a" in host:
            parsed.hostname = parse.unquote(parsed.hostname)

    config: ConfigDict = backend.config_from_url(engine, scheme, parsed)

    # Convert currentSchema option to PostgreSQL search_path
    if "currentSchema" in config["OPTIONS"]:
        value = config["OPTIONS"].pop("currentSchema")
        config["OPTIONS"]["options"] = f"-c search_path={value}"

    return config


def _handle_string_port_config(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    config: ConfigDict = backend.config_from_url(engine, scheme, url)
    # Convert port to string as required by Oracle and MSSQL
    config["PORT"] = str(config["PORT"])
    return config


def _build_pragma_init_command(pragmas: dict[str, str], pragma_overrides: dict[str, str]) -> str:
    pragmas = {**pragmas, **pragma_overrides}
    if pragmas:
        return "\n".join(f"PRAGMA {key}={value};" for key, value in pragmas.items())
    return ""


def _sqlite_parse_path(backend: Service, engine: str, scheme: str, url: str, pragmas: dict[str, str]) -> ConfigDict:
    parsed: UrlInfo = backend.parse_url(url)
    path = "/" + parsed.path
    # On windows a path like C:/a/b is parsed with C as the hostname
    # and a/b/ as the path. Reconstruct the windows path here.
    if parsed.hostname:
        path = f"{parsed.hostname}:{path}"
        parsed.location = parsed.hostname = ""
    parsed.path = path

    config: ConfigDict = backend.config_from_url(engine, scheme, parsed)

    pragmas_overrides = config.pop("PRAGMA", {})
    if init_command := _build_pragma_init_command(pragmas, pragmas_overrides):
        config["OPTIONS"]["init_command"] = init_command

    return config


@db.register(
    ("sqlite", "django.db.backends.sqlite3"),
    ("spatialite", "django.contrib.gis.db.backends.spatialite"),
)
def sqlite_config_from_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    # These special URLs cannot be parsed correctly.
    if url in ("sqlite://:memory:", "sqlite://"):
        return {
            "ENGINE": engine,
            "NAME": ":memory:",
        }

    config: ConfigDict = _sqlite_parse_path(backend, engine, scheme, url, {})

    return config


@db.register(
    ("sqlite+", "django.db.backends.sqlite3"),
)
def sqlite_plus_config_from_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    # SQLite configuration optimized for production use.
    # Based on recommendations from https://github.com/adamghill/dj-lite
    # Includes:
    # - WAL (Write-Ahead Logging) journal mode for better concurrency
    # - IMMEDIATE transaction mode to reduce lock contention
    # - Memory-mapped I/O for improved performance
    # - Optimized PRAGMA settings for production workloads

    pragmas = {
        "journal_mode": "WAL",
        "synchronous": "NORMAL",
        "temp_store": "MEMORY",
        "mmap_size": "134217728",
        "journal_size_limit": "27103364",
        "cache_size": "2000",
    }

    config: ConfigDict = _sqlite_parse_path(backend, engine, scheme, url, pragmas)
    config["OPTIONS"].setdefault("transaction_mode", "IMMEDIATE")
    config["OPTIONS"].setdefault("timeout", 5)

    return config


@db.register(
    ("postgres", "django.db.backends.postgresql"),
    ("postgis", "django.contrib.gis.db.backends.postgis"),
    # dj_database_url compat aliases
    ("postgresql", "django.db.backends.postgresql"),
    ("pgsql", "django.db.backends.postgresql"),
)
def postgresql_config_from_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    return _handle_postgres_like_config(backend, engine, scheme, url)


@db.register(
    ("mysql", "django.db.backends.mysql"),
    ("mysql+gis", "django.contrib.gis.db.backends.mysql"),
    # dj_database_url compat alias
    ("mysqlgis", "django.contrib.gis.db.backends.mysql"),
)
def mysql_config_from_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    config: ConfigDict = backend.config_from_url(engine, scheme, url)
    if "ssl-ca" in config["OPTIONS"]:
        value = config["OPTIONS"].pop("ssl-ca")
        config["OPTIONS"]["ssl"] = {"ca": value}
    return config


@db.register(
    ("oracle", "django.db.backends.oracle"),
    ("oracle+gis", "django.contrib.gis.db.backends.oracle"),
    # dj_database_url compat alias
    ("oraclegis", "django.contrib.gis.db.backends.oracle"),
)
def oracle_config_from_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    return _handle_string_port_config(backend, engine, scheme, url)


@db.register(
    ("mssql", "sql_server.pyodbc"),
    ("mssqlms", "mssql"),
)
def mssql_config_from_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    return _handle_string_port_config(backend, engine, scheme, url)


@db.register(
    ("redshift", "django_redshift_backend"),
)
def redshift_config_from_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    return _handle_postgres_like_config(backend, engine, scheme, url)


@db.register(
    ("cockroach", "django_cockroachdb"),
)
def cockroachdb_config_from_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    return backend.config_from_url(engine, scheme, url)


@db.register(
    ("timescale", "timescale.db.backends.postgresql"),
    ("timescale+gis", "timescale.db.backend.postgis"),
    # dj_database_url compat alias
    ("timescalegis", "timescale.db.backend.postgis"),
)
def timescale_config_from_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    return _handle_postgres_like_config(backend, engine, scheme, url)
