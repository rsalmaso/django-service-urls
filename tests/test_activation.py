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

"""
Tests for the zero-config activation files shipped alongside the package.

``django_service_urls.pth`` activates the settings patch on Python < 3.15, while
``django_service_urls.start`` (PEP 829) does it on Python >= 3.15, where the
``.pth`` import line is ignored because a matching ``.start`` file exists.
"""

from pathlib import Path
import pkgutil
import unittest

ROOT = Path(__file__).parent.parent
PTH = ROOT / "django_service_urls.pth"
START = ROOT / "django_service_urls.start"
ENTRY_POINT = "django_service_urls.loads:patch"


def significant_lines(path: Path) -> list[str]:
    """Return the lines PEP 829 considers meaningful (comments and blanks are ignored)."""

    lines = path.read_text(encoding="utf-8").splitlines()
    return [stripped for line in lines if (stripped := line.strip()) and not stripped.startswith("#")]


class StartFileTestCase(unittest.TestCase):
    def test_names_a_single_entry_point(self) -> None:
        self.assertEqual(significant_lines(START), [ENTRY_POINT])

    def test_entry_point_resolves_to_a_callable(self) -> None:
        # PEP 829 resolves the "colon form" with pkgutil.resolve_name and calls it
        # with no arguments, so it must resolve and be callable.
        resolved = pkgutil.resolve_name(ENTRY_POINT)
        self.assertTrue(callable(resolved))

    def test_entry_point_is_idempotent(self) -> None:
        # On Python < 3.15 the .pth import line already applies the patch, and the
        # explicit call must not wrap Settings.__init__ a second time.
        from django.conf import Settings

        patch = pkgutil.resolve_name(ENTRY_POINT)
        patch()
        first = Settings.__init__
        original = Settings._django_service_urls_original_init  # type: ignore[attr-defined]
        patch()
        self.assertIs(Settings.__init__, first)
        self.assertIs(Settings._django_service_urls_original_init, original)  # type: ignore[attr-defined]


class PthFileTestCase(unittest.TestCase):
    def test_uses_the_pep_829_straddling_form(self) -> None:
        # "import pkg.mod; pkg.mod.callable()" is the form PEP 829 recommends while
        # supporting both old and new Pythons.
        module, _, attribute = ENTRY_POINT.partition(":")
        self.assertEqual(significant_lines(PTH), [f"import {module}; {module}.{attribute}()"])


class PackagingTestCase(unittest.TestCase):
    def test_both_activation_files_land_in_the_wheel(self) -> None:
        # The wheel's force-include is what puts these files in site-packages; the
        # sdist picks them up as root files and rebuilds the wheel from them.
        # Read the line as text rather than parsing TOML, which needs Python 3.11+.
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        force_include = [line for line in pyproject.splitlines() if line.startswith("force-include")]
        self.assertEqual(len(force_include), 1, "expected exactly one force-include entry to check")
        self.assertIn(PTH.name, force_include[0])
        self.assertIn(START.name, force_include[0])


if __name__ == "__main__":
    unittest.main()
