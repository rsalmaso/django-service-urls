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

import unittest
from unittest.mock import MagicMock, patch

from django_service_urls.base import ConfigDict, Service
from django_service_urls.plugins import PluginDiscovery


def _make_entry_point(
    name: str, value: str, load_return: object = None, load_error: Exception | None = None
) -> MagicMock:
    ep = MagicMock()
    ep.name = name
    ep.value = value
    if load_error is not None:
        ep.load.side_effect = load_error
    elif load_return is not None:
        ep.load.return_value = load_return
    return ep


class PluginDiscoveryTestCase(unittest.TestCase):
    def test_discover_loads_entry_points(self) -> None:
        service = Service()
        loaded = False

        def fake_plugin() -> None:
            nonlocal loaded
            loaded = True

            @service.register(("testplugin", "test.backend"))
            def test_callback(backend: Service, engine: str, scheme: str, url: str) -> ConfigDict:
                return backend.config_from_url(engine, scheme, url)

        ep = _make_entry_point("test", "test_module")
        ep.load.side_effect = fake_plugin

        with patch("django_service_urls.plugins.importlib.metadata.entry_points", return_value=[ep]):
            discover = PluginDiscovery()
            discover()

        self.assertTrue(loaded)
        self.assertIn("testplugin", service._schemes)

    def test_discover_is_idempotent(self) -> None:
        ep = _make_entry_point("test", "test_module")

        with patch("django_service_urls.plugins.importlib.metadata.entry_points", return_value=[ep]):
            discover = PluginDiscovery()
            discover()
            discover()

        ep.load.assert_called_once()

    def test_discover_warns_on_load_failure(self) -> None:
        ep = _make_entry_point("broken", "broken_module", load_error=ImportError("No module named 'broken_module'"))

        with patch("django_service_urls.plugins.importlib.metadata.entry_points", return_value=[ep]):
            discover = PluginDiscovery()
            with self.assertWarns(UserWarning) as cm:
                discover()

        self.assertIn("broken", str(cm.warning))

    def test_discover_with_no_plugins(self) -> None:
        with patch("django_service_urls.plugins.importlib.metadata.entry_points", return_value=[]):
            discover = PluginDiscovery()
            discover()

        self.assertTrue(discover._loaded)

    def test_discover_loads_multiple_entry_points(self) -> None:
        ep1 = _make_entry_point("plugin1", "module1")
        ep2 = _make_entry_point("plugin2", "module2")

        with patch("django_service_urls.plugins.importlib.metadata.entry_points", return_value=[ep1, ep2]):
            discover = PluginDiscovery()
            discover()

        ep1.load.assert_called_once()
        ep2.load.assert_called_once()

    def test_discover_continues_after_failure(self) -> None:
        ep1 = _make_entry_point("broken", "broken_module", load_error=ImportError("bad"))
        ep2 = _make_entry_point("good", "good_module")

        with patch("django_service_urls.plugins.importlib.metadata.entry_points", return_value=[ep1, ep2]):
            discover = PluginDiscovery()
            with self.assertWarns(UserWarning):
                discover()

        ep2.load.assert_called_once()


if __name__ == "__main__":
    unittest.main()
