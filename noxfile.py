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

import os

import nox

FILES = ["service_urls", "tests", "noxfile.py"]
MAP = [
    ("3.8", ("3.2", "4.0", "4.1", "4.2")),
    ("3.9", ("3.2", "4.0", "4.1", "4.2")),
    ("3.10", ("3.2", "4.0", "4.1", "4.2", "5.0", "main")),
    ("3.11", ("4.1", "4.2", "5.0", "main")),
    ("3.12", ("4.2", "5.0", "main")),
]
DEPS = [(row[0], dependency) for row in MAP for dependency in row[1]]
nox.options.sessions = ["lint", "tests"]


def requirements_file(session, django):
    return f"py{session.python.replace('.', '')}-dj{django.replace('.', '')}.txt"


def install(session, django):
    with session.cd("requirements"):
        session.install("-r", requirements_file(session, django))


@nox.session(python="3.10")
def lint(session, django="4.2"):
    install(session, django)
    session.run("black", "--check", *FILES)
    session.run("ruff", *FILES)


@nox.session
@nox.parametrize("python,django", DEPS)
def tests(session, django):
    install(session, django)
    session.run("pytest")


@nox.session
@nox.parametrize("python,django", DEPS)
def requirements(session, django):
    django_requirements = {
        "3.2": ["django>=3.2,<4.0", "psycopg2-binary"],
        "4.0": ["django>=4.0,<4.1", "psycopg2-binary"],
        "4.1": ["django>=4.1,<4.2", "psycopg2-binary"],
        "4.2": ["django>=4.2,<5.0", "psycopg[binary]"],
        "5.0": ["django>=5.0,<5.1", "psycopg[binary]"],
        "main": ["git+https://github.com/django/django@main", "psycopg[binary]"],
    }
    session.run("pip", "install", "--upgrade", "pip", "wheel", "setuptools", "pip-tools")
    with session.cd("requirements"):
        try:
            with open("requirements.in", "wt") as fout:
                with open("../requirements.in", "rt") as fin:
                    fout.write(fin.read())
                    fout.write("django-stubs\n")
                    for requirement in django_requirements[django]:
                        fout.write(f"{requirement}\n")
                    fout.flush()
                session.run(
                    "pip-compile",
                    "--upgrade",
                    "--annotation-style=line",
                    "--resolver=backtracking",
                    f"--output-file={requirements_file(session, django)}",
                    "requirements.in",
                )
        finally:
            os.unlink("requirements.in")
