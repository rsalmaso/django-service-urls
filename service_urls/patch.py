# Copyright (C) Raffaele Salmaso <raffaele@salmaso.org>
# Copyright (C) Tom Forbes
# Copyright (C) Kenneth Reitz
#
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
# THIS SOFTWARE IS PROVIDED BY KYLE FULLER ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL KYLE FULLER BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import operator
import os

import django
from django import conf
from django.conf import (
    ENVIRONMENT_VARIABLE, LazySettings as DjangoLazySettings,
    Settings as DjangoSettings,
)
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import empty, new_method_proxy

from .services import cache, db, email


class Settings(DjangoSettings):
    def __init__(self, settings_module):
        super().__init__(settings_module)
        self.handle_service_urls()

    def handle_service_urls(self):
        setattr(self, 'DATABASES', db.parse(self.DATABASES))
        setattr(self, 'CACHES', cache.parse(self.CACHES))

        # preserve EMAIL_BACKEND backward compatibility
        if email.validate(self.EMAIL_BACKEND):
            for k, v in email.parse(self.EMAIL_BACKEND).items():
                setting = 'EMAIL_{}'.format('BACKEND' if k == 'ENGINE' else k)
                setattr(self, setting, v)
                self._explicit_settings.add(setting)


class LazySettings(DjangoLazySettings):
    settings_class = None

    def get_settings_class(self):
        return self.settings_class or Settings

    def _setup(self, name=None):
        settings_module = os.environ.get(ENVIRONMENT_VARIABLE)
        if not settings_module:
            desc = ('setting %s' % name) if name else 'settings'
            raise ImproperlyConfigured(
                'Requested %s, but settings are not configured. '
                'You must either define the environment variable %s '
                'or call settings.configure() before accessing settings.'
                % (desc, ENVIRONMENT_VARIABLE))

        self._wrapped = self.get_settings_class()(settings_module)

    if django.VERSION[:2] < (2, 0):
        # avoid maximum recursion depth exception

        def __setattr__(self, name, value):
            if name == '_wrapped':
                self.__dict__.clear()
            else:
                self.__dict__.pop(name, None)
            super(DjangoLazySettings, self).__setattr__(name, value)

        def __delattr__(self, name):
            if name == '_wrapped':
                raise TypeError("can't delete _wrapped.")
            super(DjangoLazySettings, self).__delattr__(name)
            self.__dict__.pop(name, None)

    if django.VERSION[:2] < (2, 2):
        __lt__ = new_method_proxy(operator.lt)
        __gt__ = new_method_proxy(operator.gt)


settings = LazySettings()
_patched = False


def patch():
    global _patched
    if not _patched:
        conf.Settings = Settings
        conf.LazySettings = LazySettings
        conf.settings = settings
        _patched = True


patch()
