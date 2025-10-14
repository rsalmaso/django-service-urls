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


def patch() -> None:
    """
    Patch Django's Settings.__init__ to handle all service URL parsing before
    Django's initialization completes.
    """

    import importlib

    from django.conf import Settings

    from django_service_urls.exceptions import ValidationError
    from django_service_urls.services import cache, db, email, storage, task

    if not hasattr(Settings, "_django_service_urls_original_init"):
        original_init = Settings.__init__

        def patched_init(self: Settings, settings_module: str) -> None:
            module = importlib.import_module(settings_module)

            if databases_config := getattr(module, "DATABASES", None):
                module.DATABASES = db.parse(databases_config)  # type: ignore[attr-defined]

            if caches_config := getattr(module, "CACHES", None):
                module.CACHES = cache.parse(caches_config)  # type: ignore[attr-defined]

            if storages_config := getattr(module, "STORAGES", None):
                module.STORAGES = storage.parse(storages_config)  # type: ignore[attr-defined]

            if tasks_config := getattr(module, "TASKS", None):
                module.TASKS = task.parse(tasks_config)  # type: ignore[attr-defined]

            # Try to parse as URL; if it's not a URL, it's already a backend path
            if email_backend := getattr(module, "EMAIL_BACKEND", None):
                try:
                    email_config = email.parse(email_backend)
                    for k, v in email_config.items():
                        setting = f"EMAIL_{'BACKEND' if k == 'ENGINE' else k}"
                        setattr(module, setting, v)
                except ValidationError:
                    pass

            original_init(self, settings_module)

        Settings._django_service_urls_original_init = original_init  # type: ignore[attr-defined]
        Settings.__init__ = patched_init  # type: ignore[method-assign]


patch()
