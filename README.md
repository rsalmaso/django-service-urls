# django-service-urls

`django-service-urls` is a setting helper for django to represent databases, caches and email settings via a single string.

This work is based on [dj-database-url](https://github.com/kennethreitz/dj-database-url) and [https://github.com/django/django/pull/8562](https://github.com/django/django/pull/8562).

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
```

Replace with:

```python
DATABASES = {
    'default': os.environ.get('DATABASE_DEFAULT', 'postgres://myuser:mypasswd@localhost:5432/mydb'),
}

CACHES = {
    'default': os.environ.get('CACHE_DEFAULT', ''memcached://127.0.0.1:11211'),
}
```

## Backends

Currently `django-service-urls` supports two different services:

### DATABASES (``service_urls.db``)

Service  | Backend | URLString
---------|---------|-----------
Postgresql | django.db.backends.postgresql | postgres://user:passws@host:port/db
Postgresql Socket | django.db.backends.postgresql | postgres://%2Fvar%2Frun%2Fpostgresql/db
Postgresql alias | django.db.backends.postgresql | postgresql://user:passwd@host:port/db
Postgresql alias | django.db.backends.postgresql | pgsql://user:passwd@host:port/db
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

## Installation

Install package

```shell
$ python3 -m pip install django-service-urls
```

and at the end of your main settings file add something like as

```python
import service_urls

try:
    DATABASES
except:
    pass
else:
    DATABASES = service_urls.db.parse(DATABASES)

try:
    CACHES
except:
    pass
else:
    CACHES = service_urls.cache.parse(CACHES)
```

## Changes

### dev

* Add `service_urls.db` service and defaul parsers
* Add `service_urls.cache` service and defaul parsers
