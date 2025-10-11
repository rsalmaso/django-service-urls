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

import unittest

from django_service_urls import storage


class CustomStorageTestCase(unittest.TestCase):
    def test_custom_storage_backend(self) -> None:
        result = storage.parse("storage://my.custom.StorageBackend?location=/path/to/storage&mode=private")
        self.assertEqual(result["BACKEND"], "my.custom.StorageBackend")
        self.assertEqual(result["OPTIONS"]["location"], "/path/to/storage")
        self.assertEqual(result["OPTIONS"]["mode"], "private")


class DjangoBuiltinStoragesTestCase(unittest.TestCase):
    def test_filesystem_storage(self) -> None:
        result = storage.parse("fs://?location=/var/www/media&base_url=/media/")
        self.assertEqual(result["BACKEND"], "django.core.files.storage.filesystem.FileSystemStorage")
        self.assertEqual(result["OPTIONS"]["location"], "/var/www/media")
        self.assertEqual(result["OPTIONS"]["base_url"], "/media/")

    def test_inmemory_storage(self) -> None:
        result = storage.parse("memory://")
        self.assertEqual(result["BACKEND"], "django.core.files.storage.memory.InMemoryStorage")

    def test_staticfiles_storage(self) -> None:
        result = storage.parse("static://")
        self.assertEqual(result["BACKEND"], "django.contrib.staticfiles.storage.StaticFilesStorage")

    def test_manifest_staticfiles_storage(self) -> None:
        result = storage.parse("manifest://")
        self.assertEqual(result["BACKEND"], "django.contrib.staticfiles.storage.ManifestStaticFilesStorage")


class WhitenoiseStoragesTestCase(unittest.TestCase):
    def test_whitenoise_storage(self) -> None:
        result = storage.parse("whitenoise://?max_age=31536000&autorefresh=true")
        self.assertEqual(result["BACKEND"], "whitenoise.storage.CompressedStaticFilesStorage")
        self.assertEqual(result["OPTIONS"]["max_age"], 31536000)
        self.assertEqual(result["OPTIONS"]["autorefresh"], True)

    def test_whitenoise_manifest_storage(self) -> None:
        result = storage.parse("whitenoise+static://")
        self.assertEqual(result["BACKEND"], "whitenoise.storage.CompressedManifestStaticFilesStorage")


class S3StoragesTestCase(unittest.TestCase):
    def test_s3_storage(self) -> None:
        result = storage.parse("s3://?access_key=KEY&secret_key=SECRET&object_parameters.CacheControl=max-age=86400")
        self.assertEqual(result["BACKEND"], "storages.backends.s3.S3Storage")
        self.assertEqual(result["OPTIONS"]["access_key"], "KEY")
        self.assertEqual(result["OPTIONS"]["secret_key"], "SECRET")
        self.assertEqual(result["OPTIONS"]["object_parameters"]["CacheControl"], "max-age=86400")

    def test_s3_static_storage(self) -> None:
        result = storage.parse("s3+static://")
        self.assertEqual(result["BACKEND"], "storages.backends.s3.S3StaticStorage")

    def test_s3_manifest_storage(self) -> None:
        result = storage.parse("s3+manifest://")
        self.assertEqual(result["BACKEND"], "storages.backends.s3.S3ManifestStaticStorage")

    def test_s3_with_basic_options(self) -> None:
        result = storage.parse("s3://?bucket_name=mybucket&region_name=us-east-1")
        self.assertEqual(result["BACKEND"], "storages.backends.s3.S3Storage")
        self.assertEqual(result["OPTIONS"]["bucket_name"], "mybucket")
        self.assertEqual(result["OPTIONS"]["region_name"], "us-east-1")


class CloudStoragesTestCase(unittest.TestCase):
    def test_azure_storage(self) -> None:
        result = storage.parse("azure://?account_name=myaccount&account_key=mykey&azure_container=media")
        self.assertEqual(result["BACKEND"], "storages.backends.azure_storage.AzureStorage")
        self.assertEqual(result["OPTIONS"]["account_name"], "myaccount")
        self.assertEqual(result["OPTIONS"]["account_key"], "mykey")
        self.assertEqual(result["OPTIONS"]["azure_container"], "media")

    def test_google_cloud_storage(self) -> None:
        result = storage.parse("google://?bucket_name=mybucket&project_id=myproject")
        self.assertEqual(result["BACKEND"], "storages.backends.gcloud.GoogleCloudStorage")
        self.assertEqual(result["OPTIONS"]["bucket_name"], "mybucket")
        self.assertEqual(result["OPTIONS"]["project_id"], "myproject")

    def test_dropbox_storage(self) -> None:
        result = storage.parse("dropbox://?oauth2_access_token=mytoken&root_path=/media")
        self.assertEqual(result["BACKEND"], "storages.backends.dropbox.DropboxStorage")
        self.assertEqual(result["OPTIONS"]["oauth2_access_token"], "mytoken")
        self.assertEqual(result["OPTIONS"]["root_path"], "/media")


class FileTransferStoragesTestCase(unittest.TestCase):
    def test_ftp_storage(self) -> None:
        result = storage.parse("ftp://?location=ftp.example.com&encoding=utf-8")
        self.assertEqual(result["BACKEND"], "storages.backends.ftp.FTPStorage")
        self.assertEqual(result["OPTIONS"]["location"], "ftp.example.com")
        self.assertEqual(result["OPTIONS"]["encoding"], "utf-8")

    def test_sftp_storage(self) -> None:
        result = storage.parse("sftp://?host=sftp.example.com&root_path=/uploads&port=22")
        self.assertEqual(result["BACKEND"], "storages.backends.sftpstorage.SFTPStorage")
        self.assertEqual(result["OPTIONS"]["host"], "sftp.example.com")
        self.assertEqual(result["OPTIONS"]["root_path"], "/uploads")
        self.assertEqual(result["OPTIONS"]["port"], 22)


class LibCloudStorageTestCase(unittest.TestCase):
    def test_libcloud_storage(self) -> None:
        result = storage.parse("libcloud://?provider=S3&key=mykey&secret=mysecret")
        self.assertEqual(result["BACKEND"], "storages.backends.apache_libcloud.LibCloudStorage")
        self.assertEqual(result["OPTIONS"]["provider"], "S3")
        self.assertEqual(result["OPTIONS"]["key"], "mykey")
        self.assertEqual(result["OPTIONS"]["secret"], "mysecret")


if __name__ == "__main__":
    unittest.main()
