import unittest

from service_urls import db, Service

GENERIC_TESTS = [
    (
        'username:password@domain/database',
        ('username', 'password', 'domain', '', 'database', {})
    ),
    (
        'username:password@domain:123/database',
        ('username', 'password', 'domain', 123, 'database', {})
    ),
    (
        'domain:123/database',
        ('', '', 'domain', 123, 'database', {})
    ),
    (
        'user@domain:123/database',
        ('user', '', 'domain', 123, 'database', {})
    ),
    (
        'username:password@[2001:db8:1234::1234:5678:90af]:123/database',
        ('username', 'password', '2001:db8:1234::1234:5678:90af', 123, 'database', {})
    ),
    (
        'username:password@host:123/database?reconnect=true',
        ('username', 'password', 'host', 123, 'database', {'reconnect': True})
    ),
    (
        'username:password@/database',
        ('username', 'password', '', '', 'database', {})
    ),
]


class DatabaseTestCase(unittest.TestCase):
    SCHEME = None
    STRING_PORTS = False  # Workaround for Oracle

    def test_parsing(self):
        if self.SCHEME is None:
            return
        for value, (user, passw, host, port, database, options) in GENERIC_TESTS:
            value = '{scheme}://{value}'.format(scheme=self.SCHEME, value=value)
            with self.subTest(value=value):
                result = db.parse(value)
                self.assertEqual(result['NAME'], database)
                self.assertEqual(result['HOST'], host)
                self.assertEqual(result['USER'], user)
                self.assertEqual(result['PASSWORD'], passw)
                self.assertEqual(result['PORT'], port if not self.STRING_PORTS else str(port))
                self.assertDictEqual(result['OPTIONS'], options)


class SqliteTests(DatabaseTestCase):
    SCHEME = 'sqlite'

    def test_empty_url(self):
        url = db.parse('sqlite://')
        self.assertEqual(url['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(url['NAME'], ':memory:')

    def test_memory_url(self):
        url = db.parse('sqlite://:memory:')
        self.assertEqual(url['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(url['NAME'], ':memory:')


class PostgresTests(DatabaseTestCase):
    SCHEME = 'postgres'

    def test_network_parsing(self):
        url = db.parse('postgres://uf07k1i6d8ia0v:@:5435/d8r82722r2kuvn')
        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], '')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], '')
        self.assertEqual(url['PORT'], 5435)

    def test_unix_socket_parsing(self):
        url = db.parse('postgres://%2Fvar%2Frun%2Fpostgresql/d8r82722r2kuvn')
        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], '/var/run/postgresql')
        self.assertEqual(url['USER'], '')
        self.assertEqual(url['PASSWORD'], '')
        self.assertEqual(url['PORT'], '')

        url = db.parse('postgres://C%3A%2Fvar%2Frun%2Fpostgresql/d8r82722r2kuvn')
        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(url['HOST'], 'C:/var/run/postgresql')
        self.assertEqual(url['USER'], '')
        self.assertEqual(url['PASSWORD'], '')
        self.assertEqual(url['PORT'], '')

    def test_search_path_schema_parsing(self):
        url = db.parse(
            'postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431'
            '/d8r82722r2kuvn?currentSchema=otherschema'
        )
        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 5431)
        self.assertEqual(url['OPTIONS']['options'], '-c search_path=otherschema')
        self.assertNotIn('currentSchema', url['OPTIONS'])

    def test_parsing_with_special_characters(self):
        url = db.parse('postgres://%23user:%23password@ec2-107-21-253-135.compute-1.amazonaws.com:5431/%23database')
        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(url['NAME'], '#database')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], '#user')
        self.assertEqual(url['PASSWORD'], '#password')
        self.assertEqual(url['PORT'], 5431)

    def test_database_url_with_options(self):
        # Test full options
        url = db.parse(
            'postgres://uf07k1i6d8ia0v:wegauwhgeuioweg'
            '@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn'
            '?sslrootcert=rds-combined-ca-bundle.pem&sslmode=verify-full'
        )
        self.assertEqual(url['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 5431)
        self.assertEqual(url['OPTIONS'], {
            'sslrootcert': 'rds-combined-ca-bundle.pem',
            'sslmode': 'verify-full'
        })

    def test_gis_search_path_parsing(self):
        url = db.parse(
            'postgis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431'
            '/d8r82722r2kuvn?currentSchema=otherschema'
        )
        self.assertEqual(url['ENGINE'], 'django.contrib.gis.db.backends.postgis')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 5431)
        self.assertEqual(url['OPTIONS']['options'], '-c search_path=otherschema')
        self.assertNotIn('currentSchema', url['OPTIONS'])


class MysqlTests(DatabaseTestCase):
    SCHEME = 'mysql'

    def test_with_sslca_options(self):
        url = db.parse(
            'mysql://uf07k1i6d8ia0v:wegauwhgeuioweg'
            '@ec2-107-21-253-135.compute-1.amazonaws.com:3306/d8r82722r2kuvn'
            '?ssl-ca=rds-combined-ca-bundle.pem'
        )
        self.assertEqual(url['ENGINE'], 'django.db.backends.mysql')
        self.assertEqual(url['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(url['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(url['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(url['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(url['PORT'], 3306)
        self.assertEqual(url['OPTIONS'], {
            'ssl': {
                'ca': 'rds-combined-ca-bundle.pem'
            }
        })


class OracleTests(DatabaseTestCase):
    SCHEME = 'oracle'
    STRING_PORTS = True

    def test_dsn_parsing(self):
        dsn = (
            '(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)'
            '(HOST=oraclehost)(PORT=1521)))'
            '(CONNECT_DATA=(SID=hr)))'
        )
        url = db.parse('oracle://scott:tiger@/' + dsn)
        self.assertEqual(url['ENGINE'], 'django.db.backends.oracle')
        self.assertEqual(url['USER'], 'scott')
        self.assertEqual(url['PASSWORD'], 'tiger')
        self.assertEqual(url['HOST'], '')
        self.assertEqual(url['PORT'], '')

    def test_empty_dsn_parsing(self):
        dsn = (
            '(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)'
            '(HOST=oraclehost)(PORT=1521)))'
            '(CONNECT_DATA=(SID=hr)))'
        )
        self.assertRaises(ValueError, db.parse, dsn)


class TestParseURL(unittest.TestCase):
    def setUp(self):
        self.backend = Service()

    def test_hostname_sensitivity(self):
        parsed = self.backend.parse_url('http://CaseSensitive')
        self.assertEqual(parsed['hostname'], 'CaseSensitive')

    def test_port_is_an_integer(self):
        parsed = self.backend.parse_url('http://CaseSensitive:123')
        self.assertIsInstance(parsed['port'], int)

    def test_path_strips_leading_slash(self):
        parsed = self.backend.parse_url('http://test/abc')
        self.assertEqual(parsed['path'], 'abc')

    def test_query_parameters_integer(self):
        parsed = self.backend.parse_url('http://test/?a=1')
        self.assertDictEqual(parsed['options'], {'a': 1})

    def test_query_parameters_boolean(self):
        parsed = self.backend.parse_url('http://test/?a=true&b=false')
        self.assertDictEqual(parsed['options'], {'a': True, 'b': False})

    def test_query_last_parameter(self):
        parsed = self.backend.parse_url('http://test/?a=one&a=two')
        self.assertDictEqual(parsed['options'], {'a': 'two'})

    def test_does_not_reparse(self):
        parsed = self.backend.parse_url('http://test/abc')
        self.assertIs(self.backend.parse_url(parsed), parsed)


class DictionaryTests(unittest.TestCase):
    def test_databases(self):
        result = db.parse({
            'default': 'sqlite://:memory:',
            'postgresql': 'postgres://uf07k1i6d8ia0v:@:5435/d8r82722r2kuvn',
            'mysql': {
                'ENGINE': 'django.db.backends.mysql',
                'NAME': 'd8r82722r2kuvn',
                'HOST': 'ec2-107-21-253-135.compute-1.amazonaws.com',
                'USER': 'uf07k1i6d8ia0v',
                'PASSWORD': 'wegauwhgeuioweg',
                'PORT': 3306,
            },
        })
        self.assertEqual(result['default']['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(result['default']['NAME'], ':memory:')
        self.assertEqual(result['postgresql']['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(result['postgresql']['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(result['postgresql']['HOST'], '')
        self.assertEqual(result['postgresql']['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(result['postgresql']['PASSWORD'], '')
        self.assertEqual(result['postgresql']['PORT'], 5435)
        self.assertEqual(result['mysql']['ENGINE'], 'django.db.backends.mysql')
        self.assertEqual(result['mysql']['NAME'], 'd8r82722r2kuvn')
        self.assertEqual(result['mysql']['HOST'], 'ec2-107-21-253-135.compute-1.amazonaws.com')
        self.assertEqual(result['mysql']['USER'], 'uf07k1i6d8ia0v')
        self.assertEqual(result['mysql']['PASSWORD'], 'wegauwhgeuioweg')
        self.assertEqual(result['mysql']['PORT'], 3306)


if __name__ == '__main__':
    unittest.main()
