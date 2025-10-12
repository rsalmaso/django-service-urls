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

from dataclasses import dataclass, field
from typing import Any, TypeAlias
from urllib import parse

__all__ = ["parse_url"]


def _get_host_and_port(netloc: str) -> tuple[str, int | None]:
    """
    Parse a network location string into hostname and port components.

    Handles IPv4, IPv6, domain names, with or without port numbers,
    and strips authentication credentials if present.

    Args:
        netloc: Network location string (e.g., 'localhost:5432', '[::1]:8080')

    Returns:
        Tuple of (hostname, port) where port is None if not specified

    Examples:
        >>> get_host_and_port('localhost:5432')
        ('localhost', 5432)
        >>> get_host_and_port('[::1]:8080')
        ('::1', 8080)
        >>> get_host_and_port('user:pass@db.example.com:3306')
        ('db.example.com', 3306)
        >>> get_host_and_port('localhost')
        ('localhost', None)
    """
    _, _, hostinfo = netloc.rpartition("@")
    _, have_open_br, bracketed = hostinfo.partition("[")
    if have_open_br:
        hostname, _, port = bracketed.partition("]")
        _, _, port = port.partition(":")
    else:
        hostname, _, port = hostinfo.partition(":")
    return hostname, None if not port else int(port)


CastValue: TypeAlias = int | bool | str | None
CastValues: TypeAlias = list[CastValue] | CastValue


def _cast_value(value: str) -> CastValue:
    """
    Cast a string value to its appropriate type (int, bool, str or None).

    This function automatically converts string values based on their content:
    - Integers: String representations of numbers (e.g., "123" -> 123)
    - Booleans: Common boolean representations:
      - True: "true", "t", "1", "yes", "y" (case insensitive)
      - False: "false", "f", "0", "no", "n" (case insensitive)
    - None: "null" (case insensitive) -> None
    - Strings: All other values remain as strings

    Args:
        value: The string value to convert

    Returns:
        The converted value as int, bool, None, or the original string

    Examples:
        >>> _cast_value("123"), _cast_value("hello")
        (123, 'hello')
        >>> _cast_value("true"), _cast_value("false")
        (True, False)
        >>> _cast_value("null"), _cast_value("NULL")
        (None, None)
    """

    casted_value: CastValue = value
    match value.lower():
        case "true" | "t" | "1" | "yes" | "y":
            casted_value = True
        case "false" | "f" | "0" | "no" | "n":
            casted_value = False
        case "null":
            casted_value = None
        case _:
            try:
                casted_value = int(value)
            except ValueError:
                pass
    return casted_value


def _set_nested_option(options: dict[str, Any], key: str, value: Any) -> None:
    """
    Set a nested option using dot notation.

    Creates nested dictionary structures from dot-separated keys.
    If intermediate keys don't exist, they are created as empty dictionaries.
    If a non-dict value exists at an intermediate key, it's replaced with a dict.

    Examples:
        _set_nested_option({}, 'pool.min_size', 4)
        # Result: {'pool': {'min_size': 4}}

        _set_nested_option({'pool': {'max_size': 10}}, 'pool.min_size', 4)
        # Result: {'pool': {'max_size': 10, 'min_size': 4}}
    """

    parts = key.split(".")
    current = options

    # Navigate/create the nested structure
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        elif not isinstance(current[part], dict):
            # If there's a conflict (existing non-dict value), convert to dict
            current[part] = {}
        current = current[part]

    # Set the final value
    current[parts[-1]] = value


def _parse_querystring(data: str) -> dict[str, Any]:
    """Parse a query string into a typed dictionary with nested structure support."""

    parsed_data: dict[str, Any] = parse.parse_qs(data, keep_blank_values=True)
    result: dict[str, Any] = {}
    for key, values in parsed_data.items():
        # Handle multiple values as lists
        processed_value: CastValues = (
            [_cast_value(value) for value in values] if len(values) > 1 else _cast_value(values[-1])
        )

        # Handle nested config using dot notation (e.g., TESTING.DATABASES.NAME=test)
        if "." in key:
            _set_nested_option(result, key, processed_value)
        else:
            result[key] = processed_value

    return result


@dataclass(kw_only=True)
class UrlInfo:
    scheme: str = ""
    username: str | None = None
    password: str | None = None
    hostname: str | None = None
    port: int | None = None
    path: str = ""
    fullpath: str = ""
    query: dict[str, Any] = field(default_factory=dict)
    location: list[str] | str = ""
    fragment: dict[str, Any] = field(default_factory=dict)


def parse_url(url: str | UrlInfo, *, multiple_netloc: bool = False) -> UrlInfo:
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

    # This method may be called with an already parsed URL
    if isinstance(url, UrlInfo):
        return url

    # scheme://netloc/path;parameters?query#fragment
    parsed: parse.SplitResult = parse.urlsplit(url)
    # 1) cannot have multiple files, so assume that they are always hostnames
    # 2) parsed.hostname always returns a lower-cased hostname
    #    this isn't correct if hostname is a file path, so parse with the same
    #    algorithm of _hostinfo (and cast port to int if exists)
    netlocs: list[str] = parsed.netloc.split(",") if multiple_netloc else []
    hostname, port = (None, None) if len(netlocs) > 1 else _get_host_and_port(parsed.netloc)

    return UrlInfo(
        scheme=parsed.scheme,
        username=parse.unquote(parsed.username) if parsed.username else parsed.username,
        password=parse.unquote(parsed.password) if parsed.password else parsed.password,
        hostname=parse.unquote(hostname) if hostname else hostname,
        port=port,
        path=parse.unquote(parsed.path[1:]) if parsed.path else parsed.path[1:],
        fullpath=parse.unquote(parsed.path) if parsed.path else parsed.path,
        query=_parse_querystring(parsed.query),
        location=netlocs if len(netlocs) > 1 else parsed.netloc,
        fragment=_parse_querystring(parsed.fragment),
    )
