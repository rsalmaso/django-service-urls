# Copyright (C) Raffaele Salmaso <raffaele@salmaso.org>
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

from __future__ import annotations

from types import ModuleType
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from django_service_urls.base import Service

__all__ = ["register_setting"]


class SettingsRegistry:
    """Register a custom Django setting for auto-parsing by ``loads.py``.

    Plugins call ``register_setting(setting_name, service)`` at import time.
    ``loads.py`` calls ``register_setting.apply(module)`` inside the patched
    ``Settings.__init__`` to process all registered settings.

    If *handler* is omitted the default behaviour replaces the setting
    value with ``service.parse(value)`` — the same as DATABASES / CACHES.

    A custom *handler* receives the raw settings module and can read/write
    any attributes on it, which is useful for email-style settings that fan
    out into multiple Django settings (EMAIL_BACKEND, EMAIL_HOST, …).

    Examples::

        # Default handler — dict setting, like DATABASES / CACHES
        register_setting("SEARCH_ENGINES", search)

        # Custom handler — fan-out, like EMAIL_BACKEND → EMAIL_HOST, …
        def _handler(module: ModuleType) -> None:
            if value := getattr(module, "MY_BACKEND", None):
                for k, v in my_service.parse(value).items():
                    setattr(module, f"MY_{k}", v)

        register_setting("MY_BACKEND", my_service, handler=_handler)
    """

    def __init__(self) -> None:
        self._handlers: list[Callable[[ModuleType], None]] = []

    def __call__(
        self,
        setting_name: str,
        service: Service,
        handler: Callable[[ModuleType], None] | None = None,
    ) -> None:
        if handler is None:

            def _default(module: ModuleType, _name: str = setting_name, _svc: Service = service) -> None:
                if config := getattr(module, _name, None):
                    setattr(module, _name, _svc.parse(config))

            self._handlers.append(_default)
        else:
            self._handlers.append(handler)

    def apply(self, module: ModuleType) -> None:
        for handler in self._handlers:
            handler(module)


register_setting = SettingsRegistry()
