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

from django_service_urls.base import ConfigDict, Service
from django_service_urls.parse import UrlInfo

__all__ = ["mailer"]


class MailerService(Service):
    """
    Parse mailer URLs into Django >= 6.1 ``MAILERS`` entries.

    Each entry is a ``{"BACKEND": ..., "OPTIONS": {...}}`` dictionary, where
    ``OPTIONS`` holds the lowercase keyword arguments passed to the backend.
    """

    def config_from_url(self, engine: str, scheme: str, url: str | UrlInfo, **kwargs: object) -> ConfigDict:
        config: ConfigDict = {
            "BACKEND": engine,
        }
        return config


mailer: MailerService = MailerService()


@mailer.register(
    ("smtp", "django.core.mail.backends.smtp.EmailBackend"),
    ("smtps", "django.core.mail.backends.smtp.EmailBackend"),  # smtp+tls alias
    ("smtp+tls", "django.core.mail.backends.smtp.EmailBackend"),
    ("smtp+ssl", "django.core.mail.backends.smtp.EmailBackend"),
)
def mailer_smtp_config_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    config = backend.config_from_url(engine, scheme, url)
    parsed: UrlInfo = backend.parse_url(url)
    options: ConfigDict = {
        # host is required by the SMTP backend, so always provide it.
        "host": parsed.hostname or "localhost",
    }
    if parsed.port:
        options["port"] = parsed.port
    if parsed.username:
        options["username"] = parsed.username
    if parsed.password:
        options["password"] = parsed.password
    if "use_tls" in parsed.query:
        options["use_tls"] = parsed.query.pop("use_tls")
    elif scheme in ("smtps", "smtp+tls"):
        options["use_tls"] = True
    if "use_ssl" in parsed.query:
        options["use_ssl"] = parsed.query.pop("use_ssl")
    elif scheme == "smtp+ssl":
        options["use_ssl"] = True
    for key in ("timeout", "ssl_certfile", "ssl_keyfile"):
        if key in parsed.query:
            options[key] = parsed.query.pop(key)
    # Forward any remaining query params
    options.update(parsed.query)
    config["OPTIONS"] = options
    return config


@mailer.register(
    ("console", "django.core.mail.backends.console.EmailBackend"),
)
def mailer_console_config_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    return backend.config_from_url(engine, scheme, url)


@mailer.register(
    ("file", "django.core.mail.backends.filebased.EmailBackend"),
)
def mailer_file_config_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    config = backend.config_from_url(engine, scheme, url)
    parsed: UrlInfo = backend.parse_url(url)
    path = f"/{parsed.path}"
    # On windows a path like C:/a/b is parsed with C as the hostname
    # and a/b/ as the path. Reconstruct the windows path here.
    if parsed.hostname:
        path = f"{parsed.hostname}:{path}"
    config["OPTIONS"] = {"file_path": path}
    return config


@mailer.register(
    ("memory", "django.core.mail.backends.locmem.EmailBackend"),
)
def mailer_memory_config_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    return backend.config_from_url(engine, scheme, url)


@mailer.register(
    ("dummy", "django.core.mail.backends.dummy.EmailBackend"),
)
def mailer_dummy_config_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    return backend.config_from_url(engine, scheme, url)
