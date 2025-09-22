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

from .parse import parse_url


class Service:
    validation = re.compile(r"^(?P<scheme>\S+)://\S*")

    def config_from_url(self, engine, scheme, url, **kwargs):
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

    def parse_url(self, url, *, multiple_netloc=False):
        """
        Parse URLs into components with automatic type conversion and nested structure support.

        Args:
            url: The URL string to parse, or a dict (returned as-is if already parsed)
            multiple_netloc: If True, split netloc on commas for multiple hosts

        Returns:
            Parsed URL components with keys:
                - scheme: URL scheme (e.g., 'postgresql')
                - username: URL username
                - password: URL password
                - hostname: Hostname (preserves case, unlike urlsplit)
                - port: Port as integer or None
                - path: Path without leading slash
                - fullpath: Original path with leading slash
                - query: Parsed query parameters with type conversion and nesting
                - fragment: Parsed fragment parameters with type conversion and nesting
                - location: For multiple_netloc=True, list of host:port combinations, else netloc string
        """

        return parse_url(url, multiple_netloc=multiple_netloc)

    def register(self, *args):
        def wrapper(callback):
            for scheme, engine in args:
                self._schemes[scheme] = {"callback": callback, "engine": engine}
            return callback

        return wrapper
