FROM ghcr.io/astral-sh/uv:latest AS uv

FROM ubuntu:noble

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/opt/uv/python \
    UV_PROJECT_ENVIRONMENT=/home/ubuntu/venv

ENV PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"

COPY --from=uv /uv /uvx /usr/local/bin/

# libpq5: the pure python psycopg loads the system libpq at import time
# git: the djangomain dependency group installs django from a git url
# tzdata: django >= 6.2 validates TIME_ZONE at settings init, which needs the
#         system timezone database even though the tests never use timezones
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        libpq5 \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

# Bake every interpreter the nox matrix needs, so running the tests never has to
# download one. Made world-readable because the container runs unprivileged.
# uv only puts its executables in the installing user's ~/.local/bin, which is not
# on PATH and belongs to root, so symlink them where nox can find them by name.
RUN uv python install 3.10 3.11 3.12 3.13 3.14 3.15 \
    && chmod -R a+rX /opt/uv/python \
    && for version in 3.10 3.11 3.12 3.13 3.14 3.15; do \
           ln -sf "$(uv python find "${version}")" "/usr/local/bin/python${version}"; \
       done

# docker-compose mounts named volumes on these paths; create them up front owned by
# the unprivileged user so the volumes inherit that ownership on first use. They live
# outside /app on purpose, so nothing is ever created in the bind-mounted checkout.
RUN mkdir -p /app /home/ubuntu/nox /home/ubuntu/venv /home/ubuntu/.cache/uv \
    && chown -R ubuntu:ubuntu /app /home/ubuntu

WORKDIR /app
USER ubuntu

CMD ["bash"]
