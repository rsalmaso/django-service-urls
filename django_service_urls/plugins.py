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

import importlib.metadata
import warnings

__all__ = ["discover_plugins"]

ENTRY_POINT_GROUP = "django_service_urls"


class PluginDiscovery:
    """Discover and load plugins registered via the 'django_service_urls' entry point group.

    Each entry point should point to a module that registers schemes using
    @service.register() decorators. Loading the module triggers the registration
    as a side effect.

    This callable is idempotent — calling it multiple times has no effect after
    the first successful run.
    """

    def __init__(self) -> None:
        self._loaded = False

    def __call__(self) -> None:
        if self._loaded:
            return
        self._loaded = True

        for ep in importlib.metadata.entry_points(group=ENTRY_POINT_GROUP):
            try:
                ep.load()
            except Exception as exc:
                warnings.warn(
                    f"Failed to load django_service_urls plugin {ep.name!r} ({ep.value}): {exc}",
                    stacklevel=2,
                )


discover_plugins = PluginDiscovery()
