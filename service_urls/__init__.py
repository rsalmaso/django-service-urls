from .base import Service  # noqa: F401
from .services import cache, db, email  # noqa: F401
from .version import get_version

VERSION = (1, 1, 1, 'final', 0)

__version__ = get_version(VERSION)
__author__ = 'Raffaele Salmaso'
__email__ = 'raffele@salmaso.org'
