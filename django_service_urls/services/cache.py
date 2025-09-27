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

from django_service_urls.base import ConfigDict, Service
from django_service_urls.parse import UrlInfo

__all__ = ["cache"]


class CacheService(Service):
    def config_from_url(self, engine: str, scheme: str, url: str | UrlInfo, **kwargs: Any) -> ConfigDict:
        multiple_netloc: bool = kwargs.pop("multiple_netloc", True)
        parsed: UrlInfo = self.parse_url(url, multiple_netloc=multiple_netloc)
        config: ConfigDict = {
            "BACKEND": engine,
        }
        if multiple_netloc and parsed.location:
            config["LOCATION"] = parsed.location
        else:
            if parsed.hostname:
                config["LOCATION"] = parsed.hostname
                if parsed.port:
                    config["LOCATION"] = f"{config['LOCATION']}:{parsed.port}"
        for key in ("timeout", "key_prefix", "version"):
            if key in parsed.query:
                query = parsed.query[key]
                # Only move simple values to top-level config, not nested dictionaries
                if not isinstance(query, dict):
                    query = parsed.query.pop(key)
                    config[key.upper()] = query
        config["OPTIONS"] = parsed.query
        config.update({k: v for k, v in parsed.fragment.items() if k not in config})
        return config


cache: CacheService = CacheService()


@cache.register(
    ("memory", "django.core.cache.backends.locmem.LocMemCache"),
)
def memory_config_from_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    return backend.config_from_url(engine, scheme, url)


@cache.register(
    ("db", "django.core.cache.backends.db.DatabaseCache"),
)
def db_config_from_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    return backend.config_from_url(engine, scheme, url)


@cache.register(
    ("dummy", "django.core.cache.backends.dummy.DummyCache"),
)
def dummy_config_from_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    return backend.config_from_url(engine, scheme, url)


@cache.register(
    ("pymemcached", "django.core.cache.backends.memcached.PyMemcachedCache"),
    ("memcached", "django.core.cache.backends.memcached.MemcachedCache"),  # for django <= 4.2
)
def pymemcached_config_from_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    parsed: UrlInfo = backend.parse_url(url, multiple_netloc=True)
    config: ConfigDict = backend.config_from_url(engine, scheme, parsed, multiple_netloc=True)
    if parsed.path:
        # We are dealing with a URI like pymemcached:///socket/path
        config["LOCATION"] = f"unix:/{parsed.path}"
    return config


@cache.register(
    ("pylibmccache", "django.core.cache.backends.memcached.PyLibMCCache"),
    ("memcached+pylibmccache", "django.core.cache.backends.memcached.PyLibMCCache"),  # deprecated protocol
)
def pylibmccache_config_from_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    # django >= 5.0 remove the "unix:" prefix from unix location
    # keep a different converter until we support old django versions
    parsed: UrlInfo = backend.parse_url(url, multiple_netloc=True)
    config: ConfigDict = backend.config_from_url(engine, scheme, parsed, multiple_netloc=True)
    if parsed.path:
        # We are dealing with a URI like pylibmccache:///socket/path
        config["LOCATION"] = f"/{parsed.path}"
    return config


@cache.register(
    ("file", "django.core.cache.backends.filebased.FileBasedCache"),
)
def file_config_from_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    parsed: UrlInfo = backend.parse_url(url)
    config: ConfigDict = backend.config_from_url(engine, scheme, parsed)
    path: str = f"/{parsed.path}"
    # On windows a path like C:/a/b is parsed with C as the hostname
    # and a/b/ as the path. Reconstruct the windows path here.
    if parsed.hostname:
        path = f"{parsed.hostname}:{path}"
    config["LOCATION"] = path
    return config
