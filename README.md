# django-service-urls

`django-service-urls` is a setting helper for django to represent databases, caches, email, storages and task backends via a single string.

This work is based on [dj-database-url](https://github.com/jazzband/dj-database-url) and [https://github.com/django/django/pull/8562](https://github.com/django/django/pull/8562).

### Example

Original config:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mydb',
        'HOST': 'localhost',
        'PORT': 5432,
        'USER': 'myuser',
        'PASSWORD': 'mypasswd',
        'OPTIONS': {
            'pool': {
                'min_size': 2,
                'max_size': 10,
            },
            'sslmode': 'require',
        },
        'CONN_MAX_AGE': 300,
    },
}

CACHES = {
    'default': {
        'BACKEND' : 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'OPTIONS': {
            'timeout': 300,
            'key_prefix': 'myapp',
        },
    },
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
HOST = 'localhost'
PORT = 2525
HOST_USER = ''
HOST_PASSWORD = ''
USE_TLS = True
USE_SSL = False
SSL_CERTFILE = '/etc/ssl/cert'
SSL_KEYFILE = '/etc/ssl/key'
TIMEOUT = 600
USE_LOCALTIME = False

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": "mybucket",
            "region_name": "us-east-1",
        },
    },
}

TASKS = {
    "default": {
        "BACKEND": "django_tasks.backends.database.DatabaseBackend",
        "OPTIONS": {},
    },
}
```

Replace with:

```python
DATABASES = {
    'default': os.environ.get('DATABASE_DEFAULT', 'postgres://myuser:mypasswd@localhost:5432/mydb?pool.min_size=2&pool.max_size=10&sslmode=require#CONN_MAX_AGE=300'),
}

CACHES = {
    'default': os.environ.get('CACHE_DEFAULT', 'memcached://127.0.0.1:11211?timeout=300&key_prefix=myapp'),
}

EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'smtps://localhost:2525?ssl_certfile=/etc/ssl/cert&ssl_keyfile=/etc/ssl/key&timeout=600')

STORAGES = {
    'default': os.environ.get('STORAGE_DEFAULT', 's3://?bucket_name=mybucket&region_name=us-east-1'),
}

TASKS = {
    'default': os.environ.get('TASKS_DEFAULT', 'database+dt://'),
}
```

## Advanced Features (Nested dictionaries, lists, fragments, booleans and integers)

`django-service-urls` supports **nested dictionaries** using dot notation, **lists** using repeated parameters, and **URL fragments** for top-level configuration keys.

**Boolean values** are automatically recognized: `true`, `false`, `t`, `f`, `1`, `0`, `yes`, `no`, `y`, `n` (case-insensitive).
**Integer values** are automatically converted: `123`, `0`, `999` → `int` type.

```python
# Nested options with dot notation
'postgres://user:pass@host/db?pool.min_size=2&pool.max_size=10&sslmode=require'
# → OPTIONS: {
#       'pool': {'min_size': 2, 'max_size': 10},
#       'sslmode': 'require',
#    }

# Lists with repeated parameters
'postgres://user:pass@host/db?hosts=host1&hosts=host2&hosts=host3'
# → OPTIONS: {
#       'hosts': ['host1', 'host2', 'host3'],
#    }

# Combined: nested structure with lists
'postgres://user:pass@host/db?pool.hosts=host1&pool.hosts=host2&pool.ports=5432&pool.ports=5433'
# → OPTIONS: {
#       'pool': {
#           'hosts': ['host1', 'host2'],
#           'ports': [5432, 5433],
#       },
#    }

# Deep nesting and mixed types
'postgres://user:pass@host/db?cluster.nodes.primary=node1&cluster.weights=10&cluster.weights=20&cluster.enabled=true'
# → OPTIONS: {
#       'cluster': {
#           'nodes': {'primary': 'node1'},
#           'weights': [10, 20],
#           'enabled': True,
#       },
#    }
```

### URL Fragments for Top-Level Configuration

URL fragments (after `#`) create top-level Django configuration keys, ideal for database settings like `CONN_MAX_AGE`, `AUTOCOMMIT`, or test configurations:

```python
# Database with connection settings and testing config
'postgresql://user:pass@host:5432/db?pool=true#CONN_MAX_AGE=42&TEST.DATABASES.NAME=testdb'
# → {
#     'ENGINE': 'django.db.backends.postgresql',
#     'NAME': 'db',
#     'USER': 'user', 'PASSWORD': 'pass', 'HOST': 'host', 'PORT': 5432,
#     'OPTIONS': {'pool': True},
#     'CONN_MAX_AGE': 42,
#     'TEST': {'DATABASES': {'NAME': 'testdb'}},
#   }

# Cache with top-level timeout and testing config
'redis://localhost:6379/1?timeout=300#KEY_PREFIX=prod&VERSION=2&TEST.CACHE.BACKEND=dummy'
# → {
#     'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#     'LOCATION': 'redis://localhost:6379/1',
#     'TIMEOUT': 300,
#     'KEY_PREFIX': 'prod', 'VERSION': 2,
#     'TEST': {'CACHE': {'BACKEND': 'dummy'}},
#   }
```

## URL Encoding for Credentials, Hostnames, and Paths

Username, password, hostname, and path fields are **automatically URL-decoded**,
allowing you to use special characters without manual encoding in your configuration:

```python
# Special characters in credentials are automatically decoded
'postgres://user%40domain:p%40ss%23word@localhost:5432/mydb'
# → USER: 'user@domain', PASSWORD: 'p@ss#word'

# Complex passwords with spaces and special characters
'postgres://my%2Fuser:pass%20word%21%40%23%24@localhost:5432/db'
# → USER: 'my/user', PASSWORD: 'pass word!@#$'

# Hostnames with special characters (case-sensitive)
'postgres://user:pass@My%2DServer%2EExample%2ECom:5432/db'
# → HOST: 'My-Server.Example.Com' (case preserved)

# Database names/paths with spaces and special characters (case-sensitive)
'postgres://user:pass@host:5432/My%20Database%2DName'
# → NAME: 'My Database-Name'

# SQLite file paths with spaces and special characters
'sqlite:///C%3A/Users/My%20User/AppData/My%20Database%20File.db'
# → NAME: 'C:/Users/My User/AppData/My Database File.db'

# Complex paths with multiple special characters
'postgres://user:pass@host:5432/path%2Fto%2Fdb%40company%23123'
# → NAME: 'path/to/db@company#123'
```

**When to URL-encode:**
- `@` symbol: `%40` (separates credentials from host)
- `:` symbol: `%3A` (separates username from password, or port)
- `/` symbol: `%2F` (separates components)
- `#` symbol: `%23` (starts fragment)
- `?` symbol: `%3F` (starts query string)
- `.` symbol: `%2E` (in hostnames if you need literal dots in server names)
- `-` symbol: `%2D` (in hostnames if needed)
- Space: `%20`
- Other special chars: `!` → `%21`, `$` → `%24`, etc.

**Note:** Case sensitivity is preserved for hostnames and paths during URL decoding.

**Example with environment variables:**
```python
# In your .env file or environment
DATABASE_URL="postgres://admin%40company:P%40ssw0rd%21@db.example.com:5432/production"

# In settings.py
DATABASES = {
    'default': os.environ['DATABASE_URL']
}
# → USER: 'admin@company', PASSWORD: 'P@ssw0rd!'
```

## Backends

Currently `django-service-urls` supports five different services:

### DATABASES (``django_service_urls.db``)

Service  | Backend | URLString
---------|---------|-----------
Postgresql | django.db.backends.postgresql | postgres://user:passwd@host:port/db
Postgresql Socket | django.db.backends.postgresql | postgres://%2Fvar%2Frun%2Fpostgresql/db
Postgresql (dj-database-url compat alias) | django.db.backends.postgresql | postgresql://user:passwd@host:port/db
Postgresql (dj-database-url compat alias) | django.db.backends.postgresql | pgsql://user:passwd@host:port/db
Postgis | django.contrib.gis.db.backends.postgis | postgis://user:passwd@host:port/db
Sqlite (memory) | django.db.backends.sqlite3 | sqlite://:memory: or sqlite://
Sqlite (file) | django.db.backends.sqlite3 | sqlite:///var/db/database.db
Sqlite+ (production settings) | django.db.backends.sqlite3 | sqlite+:///var/db/database.db
Spatialite (memory) | django.contrib.gis.db.backends.spatialite | spatialite://:memory: or spatialite://
Spatialite (file) | django.contrib.gis.db.backends.spatialite | spatialite:///var/db/database.db
Mysql | django.db.backends.mysql | mysql://user:passwd@host:port/db
Mysql + GIS | django.contrib.gis.db.backends.mysql | mysql+gis://user:passwd@host:port/db
Mysql GIS (dj-database-url compat alias) | django.contrib.gis.db.backends.mysql | mysqlgis://user:passwd@host:port/db
Oracle | django.db.backends.oracle | oracle://user:passwd@host:port/db
Oracle + GIS | django.contrib.gis.db.backends.oracle | oracle+gis://user:passwd@host:port/db
Oracle GIS (dj-database-url compat alias) | django.contrib.gis.db.backends.oracle | oraclegis://user:passwd@host:port/db
MSSQL | sql_server.pyodbc | mssql://user:passwd@host:port/db
MSSQL (Microsoft driver) | mssql | mssqlms://user:passwd@host:port/db
Redshift | django_redshift_backend | redshift://user:passwd@host:port/db
CockroachDB | django_cockroachdb | cockroach://user:passwd@host:port/db
Timescale | timescale.db.backends.postgresql | timescale://user:passwd@host:port/db
Timescale + GIS | timescale.db.backend.postgis | timescale+gis://user:passwd@host:port/db
Timescale GIS (dj-database-url compat alias) | timescale.db.backend.postgis | timescalegis://user:passwd@host:port/db

#### SQLite+ for Production

The `sqlite+://` protocol provides an optimized SQLite configuration for production use,
based on recommendations from [dj-lite](https://github.com/adamghill/dj-lite).
It automatically includes:

- **WAL (Write-Ahead Logging)** mode for better concurrency
- **IMMEDIATE** transaction mode to reduce lock contention
- **Memory-mapped I/O** for improved performance
- **Optimized PRAGMA settings** for production workloads

```python
# Simple production-ready configuration
DATABASES = {
    'default': 'sqlite+:///path/to/database.db'
}

# Resulting configuration:
# {
#     'ENGINE': 'django.db.backends.sqlite3',
#     'NAME': '/path/to/database.db',
#     'OPTIONS': {
#         'transaction_mode': 'IMMEDIATE',
#         'timeout': 5,
#         'init_command': '''PRAGMA journal_mode=WAL;
# PRAGMA synchronous=NORMAL;
# PRAGMA temp_store=MEMORY;
# PRAGMA mmap_size=134217728;
# PRAGMA journal_size_limit=27103364;
# PRAGMA cache_size=2000;'''
#     }
# }
```

You can override any default setting using query parameters:

```python
# Custom timeout and transaction mode
'sqlite+:///db.sqlite3?timeout=10&transaction_mode=DEFERRED'
```

**Overriding PRAGMA settings**: Use URL fragments with `PRAGMA.` prefix to override or add PRAGMA values:

```python
# Override default journal_mode
'sqlite+:///db.sqlite3#PRAGMA.journal_mode=DELETE'

# Override multiple PRAGMA settings
'sqlite+:///db.sqlite3#PRAGMA.journal_mode=DELETE&PRAGMA.synchronous=FULL'

# Add new PRAGMA settings while keeping defaults
'sqlite+:///db.sqlite3#PRAGMA.busy_timeout=5000'

# Combine with other fragment settings
'sqlite+:///db.sqlite3#PRAGMA.journal_mode=WAL&CONN_MAX_AGE=600'
```

#### SQLite with Custom PRAGMA Settings

The regular `sqlite://` protocol also supports PRAGMA settings via URL fragments:

```python
# Add PRAGMA settings to standard SQLite
DATABASES = {
    'default': 'sqlite:///path/to/db.sqlite3#PRAGMA.journal_mode=WAL&PRAGMA.synchronous=NORMAL'
}

# Works with spatialite too
DATABASES = {
    'default': 'spatialite:///path/to/spatial.db#PRAGMA.journal_mode=WAL'
}
```

This allows you to customize SQLite behavior without using the production defaults from `sqlite+://`.

### CACHES (``django_service_urls.cache``)

Service | Backend | URLString
--------|---------|-----------
Memory | django.core.cache.backends.locmem.LocMemCache | memory://
Memory | django.core.cache.backends.locmem.LocMemCache | memory://abc
Database | django.core.cache.backends.db.DatabaseCache | db://table-name
Dummy | django.core.cache.backends.dummy.DummyCache | dummy://
Dummy | django.core.cache.backends.dummy.DummyCache | dummy://abc
PyMemcached: single ip | django.core.cache.backends.memcached.PyMemcachedCache | pymemcached://1.2.3.4:1567
PyLibMCCache: single ip | django.core.cache.backends.memcached.PyLibMCCache | pylibmccache://1.2.3.4:1567
Memcached: single ip | django.core.cache.backends.memcached.MemcachedCache | memcached://1.2.3.4:1567
PyMemcached multiple ips | django.core.cache.backends.memcached.PyMemcachedCache | pymemcached://1.2.3.4:1567,1.2.3.5:1568
PyLibMCCache multiple ips | django.core.cache.backends.memcached.PyLibMCCache | pylibmccache://1.2.3.4:1567,1.2.3.5:1568
Memcached multiple ips | django.core.cache.backends.memcached.MemcachedCache | memcached://1.2.3.4:1567,1.2.3.5:1568
PyMemcached no port | django.core.cache.backends.memcached.PyMemcachedCache | pymemcached://1.2.3.4
PyLibMCCache no port | django.core.cache.backends.memcached.PyLibMCCache | pylibmccache://1.2.3.4
Memcached no port | django.core.cache.backends.memcached.MemcachedCache | memcached://1.2.3.4
PyMemcached unix socket | django.core.cache.backends.memcached.PyMemcachedCache | pymemcached:///tmp/memcached.sock
PyLibMCCache unix socket | django.core.cache.backends.memcached.PyLibMCCache | pylibmccache:///tmp/memcached.sock
Memcached unix socket | django.core.cache.backends.memcached.MemcachedCache | memcached:///tmp/memcached.sock
File | django.core.cache.backends.filebased.FileBasedCache | file://C:/abc/def/xyz
File | django.core.cache.backends.filebased.FileBasedCache | file:///abc/def/xyz

### EMAIL (``django_service_urls.email``)

Service | Backend | URLString
--------|---------|-----------
Console | django.core.mail.backends.console.EmailBackend | console://
SMTP | django.core.mail.backends.smtp.EmailBackend | smtp://localhost:25
SMTPS (smtp+tls alias) | django.core.mail.backends.smtp.EmailBackend | smtps://localhost:465
SMTP+TLS | django.core.mail.backends.smtp.EmailBackend | smtp+tls://localhost:465
SMTP+SSL | django.core.mail.backends.smtp.EmailBackend | smtp+ssl://localhost:587
File | django.core.mail.backends.filebased.EmailBackend | file:///var/log/emails
Memory | django.core.mail.backends.locmem.EmailBackend | memory://
Dummy | django.core.mail.backends.dummy.EmailBackend | dummy://

### STORAGES (``django_service_urls.storage``)

Service | Backend | URLString
--------|---------|-----------
Custom backend | (specified in URL) | storage://your.storage.Backend
FileSystem | django.core.files.storage.filesystem.FileSystemStorage | fs://
InMemory | django.core.files.storage.memory.InMemoryStorage | memory://
StaticFiles | django.contrib.staticfiles.storage.StaticFilesStorage | static://
ManifestStaticFiles | django.contrib.staticfiles.storage.ManifestStaticFilesStorage | manifest://
WhiteNoise | whitenoise.storage.CompressedStaticFilesStorage | whitenoise://
WhiteNoise + Manifest | whitenoise.storage.CompressedManifestStaticFilesStorage | whitenoise+static://
S3 | storages.backends.s3.S3Storage | s3://
S3 Static | storages.backends.s3.S3StaticStorage | s3+static://
S3 Manifest | storages.backends.s3.S3ManifestStaticStorage | s3+manifest://
LibCloud | storages.backends.apache_libcloud.LibCloudStorage | libcloud://
Azure | storages.backends.azure_storage.AzureStorage | azure://
Dropbox | storages.backends.dropbox.DropboxStorage | dropbox://
FTP | storages.backends.ftp.FTPStorage | ftp://
Google Cloud | storages.backends.gcloud.GoogleCloudStorage | google://
SFTP | storages.backends.sftpstorage.SFTPStorage | sftp://

### TASKS (``django_service_urls.task``)

Service | Backend | URLString
--------|---------|-----------
Custom backend | (specified in URL) | task://your.task.Backend
Dummy | django.tasks.backends.dummy.DummyBackend | dummy://
Immediate | django.tasks.backends.immediate.ImmediateBackend | immediate://
Dummy (django-tasks) | django_tasks.backends.dummy.DummyBackend | dummy+dt://
Immediate (django-tasks) | django_tasks.backends.immediate.ImmediateBackend | immediate+dt://
Database (django-tasks) | django_tasks.backends.database.DatabaseBackend | database+dt://
RQ (django-tasks) | django_tasks.backends.rq.RQBackend | rq+dt://

## Installation

Install package

```shell
$ python3 -m pip install django-service-urls
```

add `import django_service_urls.loads` in your `manage.py`

```python
#!/usr/bin/env python
import os
import sys

import django_service_urls.loads


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_name.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
```

and in `wsgi.py`

```python
import os
import django_service_urls.loads

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_name.settings')

application = get_wsgi_application()
```

## Handling Mixed URL and Backend Strings

In some cases, you may want to support both URL strings and traditional Django backend paths (e.g., for backward compatibility). You can use a try-except pattern with `ValidationError`:

```python
from django_service_urls import email, ValidationError

# Try to parse as URL; if it fails, treat it as a backend path
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

try:
    email_config = email.parse(EMAIL_BACKEND)
except ValidationError:
    # Not a URL, use as-is (it's a backend path string)
    pass
else:
    # Successfully parsed as URL, extract configuration
    EMAIL_BACKEND = email_config.get('ENGINE')
    EMAIL_HOST = email_config.get('HOST')
    EMAIL_PORT = email_config.get('PORT')
    # ... etc
```

This pattern is especially useful when migrating from traditional Django settings to URL-based configuration, allowing you to support both formats during the transition.

## Extend `django-service-urls`

### Add another handler

You can add another handler to an already existing handler:

`my_postgres_backend/service_url.py`
```python
from django_service_urls.services import db, postgresql_config_from_url

# postgresql fork
postgresql_config_from_url = db.register(('mypgbackend', 'my_postgres_backend'))(postgresql_config_from_url)
```

`yourapp/settings.py`
```python
import my_postgres_backend.service_url


DATABASES = {'default': 'mypgbackend://user:pwd@:/mydb'}
```

### Add another service

```python
from django_service_urls import Service


class SearchService(Service):
    def config_from_url(self, engine, scheme, url):
        parsed = self.parse_url(url)
        return {
            'ENGINE': engine,
            # here all options from parsed
        }


search = SearchService()


@search.register(('myengine', 'my_search_engine'))
def search_config_from_url(backend, engine, scheme, url):
    return backend.config_from_url(engine, scheme, url)
```

## mypy integration

If you need to load the initializer from mypy you could add

```ini
[mypy]
plugins = django_service_urls.mypy
```

in your `mypy.ini` or `setup.cfg` [file](https://mypy.readthedocs.io/en/latest/config_file.html).

[pyproject.toml](https://mypy.readthedocs.io/en/stable/config_file.html#using-a-pyproject-toml-file) configuration is also supported:

```toml
[tool.mypy]
plugins = ["django_service_urls.mypy"]
```
