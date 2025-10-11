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

__all__ = ["storage"]


class StorageService(Service):
    def config_from_url(self, engine: str, scheme: str, url: str | UrlInfo, **kwargs: Any) -> ConfigDict:
        parsed: UrlInfo = self.parse_url(url)
        config: ConfigDict = {
            "BACKEND": parsed.hostname if engine == "<backend>" else engine,
            "OPTIONS": parsed.query,
        }
        config.update({k: v for k, v in parsed.fragment.items() if k not in config})
        return config


storage: StorageService = StorageService()


@storage.register(
    # custom
    ("storage", "<backend>"),
    # django
    ("fs", "django.core.files.storage.filesystem.FileSystemStorage"),
    ("memory", "django.core.files.storage.memory.InMemoryStorage"),
    ("static", "django.contrib.staticfiles.storage.StaticFilesStorage"),
    ("manifest", "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"),
    # whitenoise
    ("whitenoise", "whitenoise.storage.CompressedStaticFilesStorage"),
    ("whitenoise+static", "whitenoise.storage.CompressedManifestStaticFilesStorage"),
    # django-storages
    ("s3", "storages.backends.s3.S3Storage"),
    ("s3+static", "storages.backends.s3.S3StaticStorage"),
    ("s3+manifest", "storages.backends.s3.S3ManifestStaticStorage"),
    ("libcloud", "storages.backends.apache_libcloud.LibCloudStorage"),
    ("azure", "storages.backends.azure_storage.AzureStorage"),
    ("dropbox", "storages.backends.dropbox.DropboxStorage"),
    ("ftp", "storages.backends.ftp.FTPStorage"),
    ("google", "storages.backends.gcloud.GoogleCloudStorage"),
    ("sftp", "storages.backends.sftpstorage.SFTPStorage"),
)
def storages_config_from_url(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
    return backend.config_from_url(engine, scheme, url)
