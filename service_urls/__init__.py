from .base import Service  # noqa: F401
from .services import db  # noqa: F401
from .version import get_version

VERSION = (0, 1, 0, "alpha", 0)

__version__ = get_version(VERSION)
__author__ = "Raffaele Salmaso"
__email__ = "raffele@salmaso.org"
