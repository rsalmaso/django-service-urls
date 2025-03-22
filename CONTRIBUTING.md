# Contributing

There are many ways to contribute to the project. You may improve the documentation, address a bug,
add some feature to the code or do something else. All sort of contributions are welcome.

## Development

This project use
- (uv)[https://docs.astral.sh/uv/] for python/dependencies management
- (ruff)[https://docs.astral.sh/ruff/] for code linter and code formatter
- (nox)[https://pypi.org/project/nox/] for running tests

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
