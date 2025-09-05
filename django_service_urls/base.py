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

import re
from urllib import parse


def _cast_value(value):
    """Cast a string value to its appropriate type (int, bool, or str)."""

    if value.isdigit():
        value = int(value)
    elif value.lower() in ("true", "t", "1", "yes", "y"):
        value = True
    elif value.lower() in ("false", "f", "0", "no", "n"):
        value = False

    return value


def _set_nested_option(options, key, value):
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


def _parse_querystring(data):
    """Parse a query string into a typed dictionary with nested structure support."""

    data = parse.parse_qs(data, keep_blank_values=True)
    result = {}
    for key, values in data.items():
        # Handle multiple values as lists
        if len(values) > 1:
            value = [_cast_value(value) for value in values]
        else:
            value = _cast_value(values[-1])

        # Handle nested config using dot notation (e.g., TESTING.DATABASES.NAME=test)
        if "." in key:
            _set_nested_option(result, key, value)
        else:
            result[key] = value

    return result


def _get_hostinfo(netloc):
    _, _, hostinfo = netloc.rpartition("@")
    _, have_open_br, bracketed = hostinfo.partition("[")
    if have_open_br:
        hostname, _, port = bracketed.partition("]")
        _, _, port = port.partition(":")
    else:
        hostname, _, port = hostinfo.partition(":")
    if not port:
        port = None
    else:
        port = int(port)
    return hostname, port


class Service:
    validation = re.compile(r"^(?P<scheme>\S+)://\S*")

    def config_from_url(self, engine, scheme, url):
        raise NotImplementedError("")

    def __init__(self):
        self._schemes = {}

    def validate(self, data):
        match = self.validation.match(data)
        return match.groups()[0] if match else None

    def _parse(self, data):
        if not isinstance(data, str):
            return data

        if not data:
            return {}

        scheme = self.validate(data)
        if scheme is None:
            raise ValueError(f"{data} is invalid, only full dsn urls (scheme://host...) allowed")
        try:
            _scheme = self._schemes[scheme]
        except KeyError:
            raise ValueError(f"{scheme}:// scheme not registered")
        callback, engine = _scheme["callback"], _scheme["engine"]
        return callback(self, engine, scheme, data)

    def parse(self, data):
        if isinstance(data, dict):
            return {k: self._parse(v) for k, v in data.items()}
        return self._parse(data)

    @staticmethod
    def parse_url(url, *, multiple_netloc=False):
        """
        Parse URLs into components with automatic type conversion and nested structure support.

        Args:
            url: The URL string to parse, or a dict (returned as-is)
            multiple_netloc: If True, split netloc on commas for multiple hosts

        Returns:
            dict: Parsed URL components with keys:
                - scheme: URL scheme (e.g., 'postgresql')
                - username: URL username
                - password: URL password
                - hostname: Hostname (preserves case, unlike urlsplit)
                - port: Port as integer or None
                - path: Path without leading slash
                - fullpath: Original path with leading slash
                - query: Parsed query parameters with type conversion and nesting
                - fragment: Parsed fragment parameters with type conversion and nesting
                - location: For multiple_netloc=True, list of host:port combinations
        """

        # This method may be called with an already parsed URL
        if isinstance(url, dict):
            return url

        # scheme://netloc/path;parameters?query#fragment
        parsed = parse.urlsplit(url)
        # 1) cannot have multiple files, so assume that they are always hostnames
        # 2) parsed.hostname always returns a lower-cased hostname
        #    this isn't correct if hostname is a file path, so parse with the same
        #    algorithm of _hostinfo (and cast port to int if exists)
        netlocs = parsed.netloc.split(",") if multiple_netloc else []
        hostname, port = (None, None) if len(netlocs) > 1 else _get_hostinfo(parsed.netloc)

        config = {
            "scheme": parsed.scheme,
            "username": parsed.username,
            "password": parsed.password,
            "hostname": hostname,
            "port": port,
            "path": parsed.path[1:],
            "fullpath": parsed.path,
            "query": _parse_querystring(parsed.query),
            "location": netlocs if len(netlocs) > 1 else parsed.netloc,
            "fragment": _parse_querystring(parsed.fragment),
        }
        return config

    def register(self, *args):
        def wrapper(func):
            for scheme, engine in args:
                self._schemes[scheme] = {"callback": func, "engine": engine}
            return func

        return wrapper
