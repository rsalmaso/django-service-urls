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

from urllib import parse

from django_service_urls.base import Service


class DatabaseService(Service):
    def config_from_url(self, engine, scheme, url):
        parsed = self.parse_url(url)
        config = {
            "ENGINE": engine,
            "NAME": parse.unquote(parsed["path"] or ""),
            "USER": parse.unquote(parsed["username"] or ""),
            "PASSWORD": parse.unquote(parsed["password"] or ""),
            "HOST": parsed["hostname"],
            "PORT": parsed["port"] or "",
            "OPTIONS": parsed["query"],
        }
        config.update({k: v for k, v in parsed["fragment"].items() if k not in config})
        return config


db = DatabaseService()


@db.register(
    ("sqlite", "django.db.backends.sqlite3"),
    ("spatialite", "django.contrib.gis.db.backends.spatialite"),
)
def sqlite_config_from_url(backend, engine, scheme, url):
    # These special URLs cannot be parsed correctly.
    if url in ("sqlite://:memory:", "sqlite://"):
        return {
            "ENGINE": engine,
            "NAME": ":memory:",
        }

    parsed = backend.parse_url(url)
    path = "/" + parsed["path"]
    # On windows a path like C:/a/b is parsed with C as the hostname
    # and a/b/ as the path. Reconstruct the windows path here.
    if parsed["hostname"]:
        path = f"{parsed['hostname']}:{path}"
        parsed["location"] = parsed["hostname"] = ""
    parsed["path"] = path
    return backend.config_from_url(engine, scheme, parsed)


@db.register(
    ("postgres", "django.db.backends.postgresql"),
    ("postgis", "django.contrib.gis.db.backends.postgis"),
    # dj_database_url compat aliases
    ("postgresql", "django.db.backends.postgresql"),
    ("pgsql", "django.db.backends.postgresql"),
)
def postgresql_config_from_url(backend, engine, scheme, url):
    parsed = backend.parse_url(url)
    host = parsed["hostname"].lower()
    # Handle postgres percent-encoded paths.
    if "%2f" in host or "%3a" in host:
        parsed["hostname"] = parse.unquote(parsed["hostname"])
    config = backend.config_from_url(engine, scheme, parsed)
    if "currentSchema" in config["OPTIONS"]:
        value = config["OPTIONS"].pop("currentSchema")
        config["OPTIONS"]["options"] = f"-c search_path={value}"
    return config


@db.register(
    ("mysql", "django.db.backends.mysql"),
    ("mysql+gis", "django.contrib.gis.db.backends.mysql"),
)
def mysql_config_from_url(backend, engine, scheme, url):
    config = backend.config_from_url(engine, scheme, url)
    if "ssl-ca" in config["OPTIONS"]:
        value = config["OPTIONS"].pop("ssl-ca")
        config["OPTIONS"]["ssl"] = {"ca": value}
    return config


@db.register(
    ("oracle", "django.db.backends.oracle"),
    ("oracle+gis", "django.contrib.gis.db.backends.oracle"),
)
def oracle_config_from_url(backend, engine, scheme, url):
    config = backend.config_from_url(engine, scheme, url)
    # Oracle requires string ports
    config["PORT"] = str(config["PORT"])
    return config
