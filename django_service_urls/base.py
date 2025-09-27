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

from collections.abc import Mapping, MutableMapping
from typing import Any, Callable, TypeAlias, TypedDict
from urllib.parse import urlsplit

from .exceptions import ValidationError
from .parse import parse_url, UrlInfo

__all__ = ["ConfigDict", "Service"]


ConfigDict: TypeAlias = MutableMapping[str, Any]
ServiceCallback: TypeAlias = Callable[["Service", str, str, str], ConfigDict]


class SchemeRegistration(TypedDict):
    """Registration information for a URL scheme."""

    engine: str
    callback: ServiceCallback


class Service:
    def config_from_url(self, engine: str, scheme: str, url: str | UrlInfo, **kwargs: Any) -> ConfigDict:
        raise NotImplementedError("")

    def __init__(self) -> None:
        self._schemes: dict[str, SchemeRegistration] = {}

    def validate(self, data: str) -> str | None:
        parsed = urlsplit(data)
        return parsed.scheme if parsed.scheme else None

    def _parse(self, data: str | ConfigDict) -> ConfigDict:
        if isinstance(data, Mapping):
            # return as is
            return data

        if not isinstance(data, str):
            # invalid input type
            raise ValidationError(f"Invalid input type: {type(data)}")

        if not data:
            # empty string
            return {}

        scheme: str | None = self.validate(data)
        if scheme is None:
            raise ValidationError(f"{data} is invalid, only full dsn urls (scheme://host...) allowed")
        try:
            _scheme: SchemeRegistration = self._schemes[scheme]
        except KeyError:
            raise ValidationError(f"{scheme}:// scheme not registered")
        callback: ServiceCallback = _scheme["callback"]
        engine: str = _scheme["engine"]
        result: ConfigDict = callback(self, engine, scheme, data)
        return result

    def parse(self, data: str | ConfigDict) -> ConfigDict:
        """
        Parse configuration data from various input formats.

        Accepts the following types of valid input:
        - Raw URL string: "scheme://config/"
        - Top-level dictionary: dict[str, str]
        - Nested dictionary: dict[str, dict[str, Any]] (returned as-is)

        Args:
            data: Configuration data as URL string or dictionary mapping

        Returns:
            dict[str, Any]: Parsed configuration dictionary

        Raises:
            ValidationError: For unsupported input types or invalid URLs
        """
        if isinstance(data, Mapping):
            return {k: self._parse(v) for k, v in data.items()}
        return self._parse(data)

    def parse_url(self, url: str | UrlInfo, *, multiple_netloc: bool = False) -> UrlInfo:
        """
        Parse URLs into components with automatic type conversion and nested structure support.

        Args:
            url: The URL string to parse, or a dict (returned as-is if already parsed)
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
            args: Tuple of scheme and engine

        Returns:
            Callable[[ServiceCallback], ServiceCallback]: Decorator function
        """

        def wrapper(callback: ServiceCallback) -> ServiceCallback:
            for scheme, engine in args:
                self._schemes[scheme] = {"callback": callback, "engine": engine}
            return callback

        return wrapper
