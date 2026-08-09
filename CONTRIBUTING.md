# Contributing

There are many ways to contribute to the project. You may improve the documentation, address a bug,
add some feature to the code or do something else. All sort of contributions are welcome.

## Development

This project use
- (uv)[https://docs.astral.sh/uv/] for python/dependencies management
- (ruff)[https://docs.astral.sh/ruff/] for code linter and code formatter
- (nox)[https://pypi.org/project/nox/] for running tests

You may work directly on your machine, as described below, or in a container that
already provides every supported `python` version: see
[Running in a container](#running-in-a-container).

### Requirements

Be sure to have installed system-wide:
- `libpq5` — the pure python `psycopg` loads the system libpq at import time
- `git` — the `djangomain` dependency group installs django from a git url
- `tzdata` — django >= 6.2 validates `TIME_ZONE` when settings are loaded

### Code linter

To lint your code, you may run:

```bash
$ uv run ruff check --fix .
```

### Code formatter

To format your code, you may run:

```bash
$ uv run ruff format .
```

### Testing

To run tests against all supported `python` and `django` versions, you may run:

```bash
$ uv run nox
```

To see all tests, you may use:

```bash
$ uv run nox --list
```

`nox` provisions any missing `python` version through `uv`, so you do not need to
install them yourself.

To run the test suite against a single version, the one `uv` picks for the project:

```bash
$ uv run pytest
```

## Running in a container

The container runs the same test matrix, so you get the same interpreters and system
libraries regardless of what is installed on your machine.

### Prerequisites

- [Docker](https://docs.docker.com/engine/install/) (includes Compose v2)
- [just](https://github.com/casey/just) — `uv tool install rust-just`

### Usage

```bash
$ just               # list the recipes
$ just build         # build the image (first run downloads the interpreters)
$ just test          # run the whole nox matrix
$ just shell         # open a shell in a container
```

Every recipe starts a throwaway container with `docker compose run --rm`, so nothing
is left running between tasks and no container can go stale against a rebuilt image.
Creating one costs about half a second, and the environments live in named volumes,
so repeat runs are still fast.

To run part of the matrix:

```bash
$ just test -s "tests(python='3.13', django='6.1')"   # one cell
$ just test -s lint                                   # one session
$ just pytest                                         # the suite on the default python
$ just pytest tests/test_parse.py -q                  # a single module
```

The remaining recipes:

```bash
$ just lint          # ruff check + format --check
$ just fmt           # ruff format + check --fix
$ just typing        # mypy
$ just down          # remove the compose network and any leftover containers
$ just clean         # also drop the cached environments (.nox, .venv, uv cache)
$ just rebuild       # rebuild the image from scratch
```

### About the image

Based on `ubuntu:noble`, with `uv`, all system dependencies and every interpreter
the matrix needs (3.10 … 3.15) baked in, so a test run never downloads one.

The checkout is bind mounted read-write at `/app`, so edits on your machine apply
immediately without rebuilding.

The environments the container builds are kept in named volumes *outside* the mount,
because they contain absolute paths and compiled binaries that only work there, and
would otherwise collide with the ones built on your machine:

- `~/nox` — the nox session virtualenvs (`NOX_ENVDIR`)
- `~/venv` — the uv project environment (`UV_PROJECT_ENVIRONMENT`)
- `~/.cache/uv` — the uv download cache, kept so repeat runs are fast

`just clean` removes those volumes; the next run repopulates them.

The container runs as the unprivileged `ubuntu` user (uid 1000), which matches the
usual host uid, so files it writes into the mount stay owned by you.
