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

from types import ModuleType
from typing import Final

ORIGINAL_INIT: Final[str] = "_django_service_urls_original_init"


def email_settings_supported() -> bool:
    """
    Return whether Django still supports the deprecated flat ``EMAIL_*`` settings.

    These settings are deprecated in favor of ``MAILERS`` and will be removed in
    Django 7.0. Detect their availability via ``global_settings`` so we don't
    inject ``EMAIL_HOST``/``EMAIL_PORT``/... into settings Django no longer reads.
    """

    from django.conf import global_settings

    return hasattr(global_settings, "EMAIL_BACKEND")


def mailers_supported() -> bool:
    """
    Return whether Django supports the ``MAILERS`` setting (added in Django 6.1).

    ``MAILERS`` is not present in ``global_settings`` until Django 7.0, so detect
    support via ``django.core.mail`` (which exposes the mailers API from 6.1).
    """

    import django.core.mail

    return hasattr(django.core.mail, "DEFAULT_MAILER_ALIAS")


def apply_service_urls(module: ModuleType) -> None:
    """
    Parse every supported service URL setting on ``module`` in place.

    Raises ``ImproperlyConfigured`` when a settings module uses a service that the
    running Django version cannot consume: ``MAILERS`` before Django 6.1, or an
    ``EMAIL_BACKEND`` service URL on Django 7.0+ (where ``EMAIL_*`` was removed).
    """

    from django.core.exceptions import ImproperlyConfigured

    from django_service_urls.exceptions import ValidationError
    from django_service_urls.registry import register_setting
    from django_service_urls.services import cache, db, email, mailer, storage, task

    if databases_config := getattr(module, "DATABASES", None):
        module.DATABASES = db.parse(databases_config)  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]

    if caches_config := getattr(module, "CACHES", None):
        module.CACHES = cache.parse(caches_config)  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]

    if storages_config := getattr(module, "STORAGES", None):
        module.STORAGES = storage.parse(storages_config)  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]

    if tasks_config := getattr(module, "TASKS", None):
        module.TASKS = task.parse(tasks_config)  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]

    if mailers_config := getattr(module, "MAILERS", None):
        if not mailers_supported():
            raise ImproperlyConfigured("The MAILERS setting requires Django 6.1 or later; use EMAIL_BACKEND instead.")
        module.MAILERS = mailer.parse(mailers_config)  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]

    if email_backend := getattr(module, "EMAIL_BACKEND", None):
        try:
            # Succeeds only when EMAIL_BACKEND is a service URL; a plain backend
            # import path raises ValidationError and is left untouched.
            email_config = email.parse(email_backend)
        except ValidationError:
            pass
        else:
            if not email_settings_supported():
                raise ImproperlyConfigured(
                    "EMAIL_BACKEND service URLs rely on the EMAIL_* settings removed in Django 7.0; "
                    "use the MAILERS setting instead."
                )
            for k, v in email_config.items():
                setting = f"EMAIL_{'BACKEND' if k == 'ENGINE' else k}"
                setattr(module, setting, v)

    register_setting.apply(module)


def patch() -> None:
    """
    Patch Django's Settings.__init__ to handle all service URL parsing before
    Django's initialization completes.
    """

    import importlib

    from django.conf import Settings

    from django_service_urls.plugins import discover_plugins

    discover_plugins()

    if not hasattr(Settings, ORIGINAL_INIT):
        original_init = Settings.__init__

        def patched_init(self: Settings, settings_module: str) -> None:
            module = importlib.import_module(settings_module)
            apply_service_urls(module)
            original_init(self, settings_module)

        setattr(Settings, ORIGINAL_INIT, original_init)
        Settings.__init__ = patched_init  # type: ignore[method-assign]


patch()
