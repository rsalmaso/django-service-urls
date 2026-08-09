# Pass recipe arguments through as real positional arguments, so values containing
# shell metacharacters survive -- e.g. just test -s "tests(python='3.13', ...)"
set positional-arguments := true

# A throwaway container per task: nothing is left running, and nothing can go stale
# against a rebuilt image. -T because these are not interactive, so the recipes also
# work from scripts and CI.
run := "docker compose run --rm -T dev"

# List the available recipes
default:
    @just --list

# Build the container image
build:
    docker compose build

# Rebuild the container image from scratch
rebuild:
    docker compose build --no-cache

# Open a shell in a fresh container
shell:
    docker compose run --rm dev bash

# Run the whole matrix, or part of it:
#   just test -s "tests(python='3.13', django='6.1')"
test *ARGS:
    {{ run }} uv run nox "$@"

# Run pytest directly for a fast, targeted run:
#   just pytest tests/test_parse.py
pytest *ARGS:
    {{ run }} uv run pytest "$@"

# Check formatting and lint rules
lint:
    {{ run }} uv run ruff check django_service_urls tests noxfile.py
    {{ run }} uv run ruff format --check django_service_urls tests noxfile.py

# Reformat and apply the fixable lint rules
fmt:
    {{ run }} uv run ruff format django_service_urls tests noxfile.py
    {{ run }} uv run ruff check --fix django_service_urls tests noxfile.py

# Type check
typing:
    {{ run }} uv run mypy django_service_urls tests noxfile.py

# Remove the compose network and any leftover containers
down:
    docker compose down --remove-orphans

# Also drop the cached environments (.nox, .venv, uv cache)
clean:
    docker compose down --remove-orphans --volumes
