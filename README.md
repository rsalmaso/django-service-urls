# django-service-urls

`django-service-urls` is a setting helper for django to represent databases, caches and email settings via a single string.

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
    },
}

CACHES = {
    'default': {
        'BACKEND' : 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
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
```

Replace with:

```python
DATABASES = {
    'default': os.environ.get('DATABASE_DEFAULT', 'postgres://myuser:mypasswd@localhost:5432/mydb'),
}

CACHES = {
    'default': os.environ.get('CACHE_DEFAULT', 'memcached://127.0.0.1:11211'),
}

EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'smtps://localhost:2525?ssl_certfile=/etc/ssl/cert&ssl_keyfile=/etc/ssl/key&timeout=600')
```

## Backends

Currently `django-service-urls` supports three different services:

### DATABASES (``service_urls.db``)

Service  | Backend | URLString
---------|---------|-----------
Postgresql | django.db.backends.postgresql | postgres://user:passws@host:port/db
Postgresql Socket | django.db.backends.postgresql | postgres://%2Fvar%2Frun%2Fpostgresql/db
Postgresql (dj-database-url compat alias) | django.db.backends.postgresql | postgresql://user:passwd@host:port/db
Postgresql (dj-database-url compat alias) | django.db.backends.postgresql | pgsql://user:passwd@host:port/db
Postgis | django.contrib.gis.db.backends.postgis | postgis://user:passwd@host:port/db
Sqlite (memory) | django.db.backends.sqlite3 | sqlite://:memory: or sqlite://
Sqlite (file) | django.db.backends.sqlite3 | sqlite:///var/db/database.db
Spatialite (memory) | django.contrib.gis.db.backends.spatialite | spatialite://:memory: or spatialite://
Spatialite (file) | django.contrib.gis.db.backends.spatialite | spatialite:///var/db/database.db
Mysql | django.db.backends.mysql | mysql://user:passwd@host:port/db
Mysql + GIS | django.contrib.gis.db.backends.mysql | mysql+gis://user:passwd@host:port/db
Oracle | django.db.backends.oracle | oracle://user:passwd@host:port/db
Oracle + GIS | django.contrib.gis.db.backends.oracle | oracle+gis://user:passwd@host:port/db

### CACHES (``service_urls.cache``)

Service | Backend | URLString
--------|---------|-----------
Memory | django.core.cache.backends.locmem.LocMemCache | memory://
Memory | django.core.cache.backends.locmem.LocMemCache | memory://abc
Database | django.core.cache.backends.db.DatabaseCache | db://table-name
Dummy | django.core.cache.backends.dummy.DummyCache | dummy://
Dummy | django.core.cache.backends.dummy.DummyCache | dummy://abc
Memcached: single ip | django.core.cache.backends.memcached.MemcachedCache | memcached://1.2.3.4:1567
Memcached+PyLibMCCache: single ip | django.core.cache.backends.memcached.PyLibMCCache | memcached+pylibmccache://1.2.3.4:1567
Memcached multiple ips | django.core.cache.backends.memcached.MemcachedCache | memcached://1.2.3.4:1567,1.2.3.5:1568
Memcached+PyLibMCCache multiple ips | django.core.cache.backends.memcached.PyLibMCCache | memcached+pylibmccache://1.2.3.4:1567,1.2.3.5:1568
Memcached no port | django.core.cache.backends.memcached.MemcachedCache | memcached://1.2.3.4
Memcached+PyLibMCCache no port | django.core.cache.backends.memcached.PyLibMCCache | memcached+pylibmccache://1.2.3.4
Memcached unix socket | django.core.cache.backends.memcached.MemcachedCache | memcached:///tmp/memcached.sock
Memcached+PyLibMCCache unix socket | django.core.cache.backends.memcached.PyLibMCCache | memcached+pylibmccache:///tmp/memcached.sock
File | django.core.cache.backends.filebased.FileBasedCache | file://C:/abc/def/xyz
File | django.core.cache.backends.filebased.FileBasedCache | file:///abc/def/xyz

### EMAIL (``service_urls.email``)

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

## Installation

Install package

```shell
$ python3 -m pip install django-service-urls
```

add `import service_urls.patch` in your `manage.py`

```python
#!/usr/bin/env python
import os
import sys

import service_urls.patch


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
import service_urls.patch

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_name.settings')

application = get_wsgi_application()
```

## Extend `django-service-urls`

### Add another handler

You can add another handler to an already existing handler:

`my_postgres_backend/service_url.py`
```python
from service_urls.services import db, postgresql_config_from_url

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
from service_urls import Service


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

## Changes

### dev

* use declarative config in setup.cfg
* add support for Django 3.2, 4.0, and 4.1
* add support for Python 3.8, 3.9, 3.10, and 3.11

### 1.2.0

* add __lt__ and __gt__ when using Django < 2.2
* correct settings operations under django > 1.11 (ie: when running tests which override values)
* add Django 2.2 support

### 1.1.1

* correct sqlite parser

### 1.1.0

* add helper to monkey patch django settings
* doc cleanup

### 1.0.2

* fix setup.py and MANIFEST.in

### 1.0.1

* fix README typos

### 1.0.0

* Add `service_urls.db` service and default parsers
* Add `service_urls.cache` service and default parsers
* Add `service_urls.email` service and default parsers
