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

from django_service_urls.base import Service


class EmailService(Service):
    def config_from_url(self, engine, scheme, url, **kwargs):
        _parsed = self.parse_url(url)
        config = {
            "ENGINE": engine,
        }
        return config


email = EmailService()


@email.register(
    ("smtp", "django.core.mail.backends.smtp.EmailBackend"),
    ("smtps", "django.core.mail.backends.smtp.EmailBackend"),  # smtp+tls alias
    ("smtp+tls", "django.core.mail.backends.smtp.EmailBackend"),
    ("smtp+ssl", "django.core.mail.backends.smtp.EmailBackend"),
)
def email_smtp_config_url(backend, engine, scheme, url):
    config = backend.config_from_url(engine, scheme, url)
    parsed = backend.parse_url(url)
    return {
        "HOST": parsed.hostname or "localhost",
        "PORT": parsed.port or 25,
        "HOST_USER": parsed.username or "",
        "HOST_PASSWORD": parsed.password or "",
        "USE_TLS": parsed.query.get("use_tls", scheme in ("smtps", "smtp+tls")),
        "USE_SSL": parsed.query.get("use_ssl", scheme == "smtp+ssl"),
        "SSL_CERTFILE": parsed.query.get("ssl_certfile", None),
        "SSL_KEYFILE": parsed.query.get("ssl_keyfile", None),
        "TIMEOUT": parsed.query.get("timeout", None),
        "USE_LOCALTIME": parsed.query.get("use_localtime", False),
        **config,
    }


@email.register(
    ("console", "django.core.mail.backends.console.EmailBackend"),
)
def email_console_config_url(backend, engine, scheme, url):
    return backend.config_from_url(engine, scheme, url)


@email.register(
    ("file", "django.core.mail.backends.filebased.EmailBackend"),
)
def email_file_config_url(backend, engine, scheme, url):
    config = backend.config_from_url(engine, scheme, url)
    parsed = backend.parse_url(url)
    path = f"/{parsed.path}"
    # On windows a path like C:/a/b is parsed with C as the hostname
    # and a/b/ as the path. Reconstruct the windows path here.
    if parsed.hostname:
        path = f"{parsed.hostname}:{path}"
    return {
        "FILE_PATH": path,
        **config,
    }


@email.register(
    ("memory", "django.core.mail.backends.locmem.EmailBackend"),
)
def email_memory_config_url(backend, engine, scheme, url):
    return backend.config_from_url(engine, scheme, url)


@email.register(
    ("dummy", "django.core.mail.backends.dummy.EmailBackend"),
)
def email_dummy_config_url(backend, engine, scheme, url):
    return backend.config_from_url(engine, scheme, url)
