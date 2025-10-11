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


def setup(set_prefix: bool = True) -> None:
    import django
    from django.conf import settings

    from django_service_urls.exceptions import ValidationError
    from django_service_urls.services import cache, db, email, storage, task

    settings.DATABASES = db.parse(settings.DATABASES)
    settings.CACHES = cache.parse(settings.CACHES)

    if hasattr(settings, "STORAGES"):
        settings.STORAGES = storage.parse(settings.STORAGES)

    if hasattr(settings, "TASKS"):
        settings.TASKS = task.parse(settings.TASKS)

    # Preserve EMAIL_BACKEND backward compatibility
    # Try to parse as URL; if it's not a URL, it's already a backend path
    try:
        email_config = email.parse(settings.EMAIL_BACKEND)
    except ValidationError:
        # EMAIL_BACKEND is not a URL, leave it as-is (it's a backend path)
        pass
    else:
        # Only process if parse was successful
        for k, v in email_config.items():
            setting = f"EMAIL_{'BACKEND' if k == 'ENGINE' else k}"
            setattr(settings, setting, v)

    django._django_service_urls_original_django_setup(set_prefix)  # type: ignore[attr-defined]


def patch() -> None:
    import django

    if not getattr(django, "_django_service_urls_original_setup", None):
        django._django_service_urls_original_django_setup = django.setup  # type: ignore[attr-defined]
        django.setup = setup


patch()
