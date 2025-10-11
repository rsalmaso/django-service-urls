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

from collections.abc import MutableMapping
from typing import Any, Callable, TypeAlias, TypedDict
from urllib.parse import urlsplit

from .exceptions import ValidationError
from .parse import parse_url, UrlInfo

__all__ = ["ConfigDict", "Service"]


ConfigDict: TypeAlias = MutableMapping[str, Any]
ServiceCallback: TypeAlias = Callable[["Service", str, str, str], ConfigDict]


class SchemeRegistration(TypedDict):
    engine: str
    callback: ServiceCallback


class Service:
    def config_from_url(self, engine: str, scheme: str, url: str | UrlInfo, **kwargs: Any) -> ConfigDict:
        """Convert URL to Django configuration dictionary. Must be implemented by subclasses."""

        raise NotImplementedError("")

    def __init__(self) -> None:
        self._schemes: dict[str, SchemeRegistration] = {}

    def parse(self, data: str | ConfigDict) -> ConfigDict:
        """
        Parse URL strings or configuration dictionaries into Django configs.

        Args:
            data: a django configuration data or an URL string

        Examples:
            >>> service.parse("postgres://user:password@localhost:5432/dbname")
            {"ENGINE": "django.db.backends.postgresql", "NAME": "dbname", "USER": "user", "PASSWORD": "password", "HOST": "localhost", "PORT": 5432}

            >>> service.parse("unregistered://user:password@localhost:5432/dbname")
            ValidationError: ["'unregistered://' scheme is not registered"]

            >>> service.parse({"ENGINE": "django.db.backends.postgresql"})
            ValidationError: {'ENGINE': ["'django.db.backends.postgresql' is invalid, only full dsn urls (scheme://host...) are allowed"]}

            >>> service.parse({"default": "postgres://user:password@localhost:5432/dbname", "db2": {"ENGINE": "django.db.backends.postgresql"}})
            {"default": {"ENGINE": "django.db.backends.postgresql", "NAME": "dbname", "USER": "user", "PASSWORD": "password", "HOST": "localhost", "PORT": 5432}, "db2": {"ENGINE": "django.db.backends.postgresql"}}

            >>> service.parse({"default": {"ENGINE": "django.db.backends.postgresql", "NAME": "dbname", "USER": "user", "PASSWORD": "password", "HOST": "localhost", "PORT": 5432}, "db2": "django.db.backends.postgresql", "db3": "mydb://user:password@localhost:5432/dbname"})
            ValidationError: {
                'db2': ["'django.db.backends.postgresql' is invalid, only full dsn urls (scheme://host...) are allowed"],
                'db3': ["'mydb://' scheme is not registered"],
            }
        """  # noqa: E501

        if isinstance(data, dict):
            errors: dict[str, ValidationError] = {}
            parsed_data: dict[str, ConfigDict] = {}
            for key, value in data.items():
                try:
                    parsed_data[key] = value if isinstance(value, dict) else self._parse(value)
                except ValidationError as exc:
                    errors[key] = exc
            if errors:
                raise ValidationError(errors)
            return parsed_data
        elif isinstance(data, str):
            return self._parse(data)
        raise ValidationError(f"Invalid input type: {type(data)}")  # invalid input type

    def parse_url(self, url: str | UrlInfo, *, multiple_netloc: bool = False) -> UrlInfo:
        """
        Parse URLs into components with automatic type conversion and nested structure support.

        Args:
            url: The URL string to parse, or a UrlInfo data object (returned as-is if already parsed)
            multiple_netloc: If True, split netloc on commas for multiple hosts

        Returns:
            Parsed URL components with keys:
                - scheme: URL scheme (e.g., 'postgresql')
                - username: URL username (or None)
                - password: URL password (or None)
                - hostname: Hostname (preserves case, unlike urlsplit, or None)
                - port: Port as integer or None
                - path: Path without leading slash
                - fullpath: Original path with leading slash
                - query: Parsed query parameters with type conversion and nesting
                - fragment: Parsed fragment parameters with type conversion and nesting
                - location: For multiple_netloc=True, list of host:port combinations, else netloc string
        """

        return parse_url(url, multiple_netloc=multiple_netloc)

    def register(self, *args: tuple[str, str]) -> Callable[[ServiceCallback], ServiceCallback]:
        """
        Register a service callback with a scheme and engine.

        Args:
            args: (scheme, engine) tuple of schemes and engines to register

        Example:
            >>> @service.register(("postgres", "django.db.backends.postgresql"))
            ... def postgres_config(service, engine, scheme, url):
            ...     return service.config_from_url(engine, scheme, url)

        Returns:
            Callable[[ServiceCallback], ServiceCallback]: Decorator function
        """

        def wrapper(callback: ServiceCallback) -> ServiceCallback:
            for scheme, engine in args:
                self._schemes[scheme] = {"callback": callback, "engine": engine}
            return callback

        return wrapper

    def _parse(self, data: str) -> ConfigDict:
        """
        Parse URL string into Django configuration dictionary.

        Accepts the following types of valid input:
        - Raw URL string: "scheme://config/"
        - Empty string: {}

        Args:
            data: Configuration data as URL string

        Returns:
            Parsed django configuration

        Raises:
            ValidationError: For unsupported input types or invalid URLs (ValueError)

        Examples:
            >>> service._parse("postgres://user:password@localhost:5432/dbname")
            {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": "dbname",
                "USER": "user",
                "PASSWORD": "password",
                "HOST": "localhost",
                "PORT": 5432,
            }

            >>> service._parse("unregistered://user:password@localhost:5432/dbname")
            ValidationError: ["'unregistered://' scheme is not registered"]

            >>> service._parse("django.db.backends.postgresql")
            ValidationError: ["'django.db.backends.postgresql' is invalid, only full dsn urls (scheme://host...) are allowed"]
        """  # noqa: E501

        if not isinstance(data, str):
            raise ValidationError(f"Invalid input type: {type(data)}")  # invalid input type

        if not data:
            return {}  # empty string treated as empty dict

        scheme = urlsplit(data).scheme
        if not scheme:
            raise ValidationError(f"{data!r} is invalid, only full dsn urls (scheme://host...) are allowed")

        try:
            _scheme: SchemeRegistration = self._schemes[scheme]
        except KeyError:
            scheme_with_colon = f"{scheme}://"
            raise ValidationError(f"{scheme_with_colon!r} scheme is not registered")
        callback: ServiceCallback = _scheme["callback"]
        engine: str = _scheme["engine"]
        result: ConfigDict = callback(self, engine, scheme, data)
        return result
