from urllib import parse

from .base import Service


class DbService(Service):
    def config_from_url(self, engine, scheme, url):
        parsed = self.parse_url(url)
        return {
            'ENGINE': engine,
            'NAME': parse.unquote(parsed['path'] or ''),
            'USER': parse.unquote(parsed['username'] or ''),
            'PASSWORD': parse.unquote(parsed['password'] or ''),
            'HOST': parsed['hostname'],
            'PORT': parsed['port'] or '',
            'OPTIONS': parsed['options']
        }


db = DbService()


@db.register(('sqlite', 'django.db.backends.sqlite3'), ('spatialite', 'django.contrib.gis.db.backends.spatialite'))
def sqlite_config_from_url(backend, engine, scheme, url):
    # These special URLs cannot be parsed correctly.
    if url in ('sqlite://:memory:', 'sqlite://'):
        return {
            'ENGINE': engine,
            'NAME': ':memory:'
        }
    return backend.config_from_url(engine, scheme, url)


@db.register(
    ('postgres', 'django.db.backends.postgresql'), ('postgis', 'django.contrib.gis.db.backends.postgis'),
    # dj_database_url compat aliases
    ('postgresql', 'django.db.backends.postgresql'), ('pgsql', 'django.db.backends.postgresql'),
)
def postgresql_config_from_url(backend, engine, scheme, url):
    parsed = backend.parse_url(url)
    host = parsed['hostname'].lower()
    # Handle postgres percent-encoded paths.
    if '%2f' in host or '%3a' in host:
        parsed['hostname'] = parse.unquote(parsed['hostname'])
    config = backend.config_from_url(engine, scheme, parsed)
    if 'currentSchema' in config['OPTIONS']:
        value = config['OPTIONS'].pop('currentSchema')
        config['OPTIONS']['options'] = '-c search_path={0}'.format(value)
    return config


@db.register(('mysql', 'django.db.backends.mysql'), ('mysql+gis', 'django.contrib.gis.db.backends.mysql'))
def mysql_config_from_url(backend, engine, scheme, url):
    config = backend.config_from_url(engine, scheme, url)
    if 'ssl-ca' in config['OPTIONS']:
        value = config['OPTIONS'].pop('ssl-ca')
        config['OPTIONS']['ssl'] = {'ca': value}
    return config


@db.register(('oracle', 'django.db.backends.oracle'), ('oracle+gis', 'django.contrib.gis.db.backends.oracle'))
def oracle_config_from_url(backend, engine, scheme, url):
    config = backend.config_from_url(engine, scheme, url)
    # Oracle requires string ports
    config['PORT'] = str(config['PORT'])
    return config
