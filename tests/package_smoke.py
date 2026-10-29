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
Smoke check for the installed wheel, run by ``nox -s package`` outside the checkout.

The test suite imports the source tree, so it cannot see what users actually get:
the wheel installed with only its declared runtime dependencies, the activation
files in site-packages, and the settings patch applied at interpreter startup.
"""

from pathlib import Path
import sys
import sysconfig
from typing import NoReturn


def fail(message: str) -> NoReturn:
    raise SystemExit(f"package smoke check failed: {message}")


def main() -> None:
    # Checked before this script imports anything from the package: the .pth file
    # (Python < 3.15) or the .start file (>= 3.15) must have imported it at startup.
    if "django_service_urls.loads" not in sys.modules:
        try:
            import django_service_urls.loads
        except Exception as exc:
            fail(f"the activation file did not run at startup; importing it fails with {exc!r}")
        fail("the activation file did not run at startup")

    from django.conf import Settings

    import django_service_urls
    from django_service_urls import db
    from django_service_urls.loads import ORIGINAL_INIT

    purelib = Path(sysconfig.get_paths()["purelib"]).resolve()
    package_dir = Path(django_service_urls.__file__).resolve().parent
    if package_dir.parent != purelib:
        fail(f"imported {package_dir}, not the installed wheel in {purelib}")
    for name in ("django_service_urls.pth", "django_service_urls.start"):
        if not (purelib / name).is_file():
            fail(f"{name} is missing from {purelib}")
    if not (package_dir / "py.typed").is_file():
        fail(f"py.typed is missing from {package_dir}")
    if not hasattr(Settings, ORIGINAL_INIT):
        fail("Settings.__init__ is not patched")
    if db.parse("sqlite://:memory:")["ENGINE"] != "django.db.backends.sqlite3":
        fail("the installed db service did not parse a sqlite URL")

    print(f"package smoke check passed on Python {sys.version.split()[0]}")


if __name__ == "__main__":
    main()
