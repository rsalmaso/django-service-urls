# Changelog

## dev

* add support for `django.core.cache.backends.memcached.PyMemcacheCache` as `pymemcached:` protocol

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
