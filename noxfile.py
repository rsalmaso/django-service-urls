import os

import nox

FILES = ["service_urls", "tests", "noxfile.py"]
MAP = [
    ("3.8", ("3.2", "4.0", "4.1", "4.2")),
    ("3.9", ("3.2", "4.0", "4.1", "4.2")),
    ("3.10", ("3.2", "4.0", "4.1", "4.2", "main")),
    ("3.11", ("4.1", "4.2", "main")),
    ("3.12", ("main",)),
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
        "main": [
            "git+https://github.com/django/django@main",
            "psycopg" if session.python == "3.12" else "psycopg[binary]",
        ],
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
                    "--annotation-style=line",
                    "--resolver=backtracking",
                    f"--output-file={requirements_file(session, django)}",
                    "requirements.in",
                )
        finally:
            os.unlink("requirements.in")
