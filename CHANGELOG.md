# Changelog

## 2.0.0

* added support for python 3.14
* added support for django 6.0
* exctract `Service.parse_url` staticmethod into `parse.parse_url` free function
* refactored the `parse_url` function, now returns a dedicated dataclass
* allowed null values in query string/fragments
* added typing to the codebase
* added `storage` service
* added `task` service
* added Mysql GIS and Oracle GIS dj-database-url alias
* added MSSQL, Redshift, CockroachDB and Timescale service urls
* removed `Service.validate()` method
* automatically unquote UrlInfo attributes (username, password, hostname, path and fullpath)
* BREAKING: removed `service_urls` shim
* added `sqlite+://` protocol for production-optimized SQLite configuration
* added PRAGMA configuration support via URL fragments for `sqlite://`, `spatialite://`, and `sqlite+://` protocols

## 1.9.0

* refactor and updated tests
* refactor services code (split into separate modules)
* added support for complex values (nested dictionaries, list) in querystring
* extended support for boolean values
* added support for extra keys using fragment urls
* replaced `urlparse` with `urlsplit`
* always recreate the virtualenv when runnin nox with uv
* drop support for python 3.8 and 3.9

## 1.8.0

* update ruff to 0.11.2
* switch development to uv/nox[uv] and replace custom requirements with uv.lock file
* upgrade all requirements to latest version
* add CONTRIBUTING.md docs
* refactor Django integration (to preserve default translations)

## 1.7.0

* made empty string value (`""`) parse as empty dictionary (`{}`)

## 1.6.0

* BREAKING: renamed module from `service_urls` to `django_service_urls`
* added mypy plugin

## 1.5.0

* test django 4.2 with python 3.12
* add support for Django 5.0

## 1.4.1

* update memcache service protocols in README.md

## 1.4.0

* add support for `django.core.cache.backends.memcached.PyMemcacheCache` as `pymemcached:` protocol
* rename `memcached+pylibmccache` protocol to `pylibmccache`
* fix parsing of `pylibmccache` service
* add support for Python 3.12
* add nox support
* test `service_urls.patch` (monkeypatch django settings)
* cleanup license wording
  (replace wrong copyright holder name with more generic "THE COPYRIGHT HOLDERS AND CONTRIBUTORS")

## 1.3.0

* use declarative config in setup.cfg
* add support for Django 3.2, 4.0, 4.1, and 4.2
* add support for Python 3.8, 3.9, 3.10, and 3.11
* drop support for Django < 3.2
* drop support for Python < 3.8
* format code with black
* switch to ruff from flake8/isort

## 1.2.0

* add __lt__ and __gt__ when using Django < 2.2
* correct settings operations under django > 1.11 (ie: when running tests which override values)
* add Django 2.2 support

## 1.1.1

* correct sqlite parser

## 1.1.0

* add helper to monkey patch django settings
* doc cleanup

## 1.0.2

* fix setup.py and MANIFEST.in

## 1.0.1

* fix README typos

## 1.0.0

* Add `service_urls.db` service and default parsers
* Add `service_urls.cache` service and default parsers
* Add `service_urls.email` service and default parsers
