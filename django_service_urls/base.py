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
        A method to parse URLs into components that handles quirks
        with the stdlib urlparse, such as lower-cased hostnames.
        Also parses querystrings into typed components.
        """
        # This method may be called with an already parsed URL
        if isinstance(url, dict):
            return url

        # scheme://netloc/path;parameters?query#fragment
        parsed = parse.urlparse(url)
        # 1) cannot have multiple files, so assume that they are always hostnames
        # 2) parsed.hostname always returns a lower-cased hostname
        #    this isn't correct if hostname is a file path, so use '_hostinfo'
        #    to get the actual host
        netlocs = parsed.netloc.split(",") if multiple_netloc else []
        hostname, port = (None, None) if len(netlocs) > 1 else parsed._hostinfo
        if port:
            port = int(port)

        query = parse.parse_qs(parsed.query)
        options = {}
        for key, values in query.items():
            value = values[-1]
            if value.isdigit():
                value = int(value)
            elif value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            options[key] = value
        path = parsed.path[1:]

        config = {
            "scheme": parsed.scheme,
            "username": parsed.username,
            "password": parsed.password,
            "hostname": hostname,
            "port": port,
            "path": path,
            "fullpath": parsed.path,
            "options": options,
            "location": netlocs if len(netlocs) > 1 else parsed.netloc,
        }
        return config

    def register(self, *args):
        def wrapper(func):
            for scheme, engine in args:
                self._schemes[scheme] = {"callback": func, "engine": engine}
            return func

        return wrapper
