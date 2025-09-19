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

import nox

FILES = ["django_service_urls", "service_urls", "tests", "noxfile.py"]
MAP = [
    ("3.10", ("3.2", "4.0", "4.1", "4.2", "5.0", "5.1", "5.2")),
    ("3.11", ("4.1", "4.2", "5.0", "5.1", "5.2")),
    ("3.12", ("4.2", "5.0", "5.1", "5.2", "6.0", "main")),
    ("3.13", ("5.1", "5.2", "6.0", "main")),
    ("3.14", ("5.2", "6.0", "main")),
]
DEPS = [(row[0], dependency) for row in MAP for dependency in row[1]]

nox.options.sessions = ["lint", "tests"]
nox.options.reuse_existing_virtualenvs = False
nox.options.error_on_external_run = True
nox.options.default_venv_backend = "uv|virtualenv"


def install(session, django):
    pyproject = nox.project.load_toml("pyproject.toml")
    session.install(
        *nox.project.dependency_groups(pyproject, "dev"),
        *nox.project.dependency_groups(pyproject, f"django{django.replace('.', '')}"),
    )


@nox.session(python="3.10")
def lint(session, django="4.2"):
    install(session, django)
    session.run("ruff", "format", "--check", *FILES)
    session.run("ruff", "check", *FILES)


@nox.session
@nox.parametrize("python,django", DEPS)
def tests(session, django):
    install(session, django)
    session.run("pytest")
