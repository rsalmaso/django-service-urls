#!/usr/bin/env python3
import io

import service_urls
from setuptools import find_packages, setup

with io.open('README.md', "rt", encoding='utf-8') as fp:
    long_description = fp.read()


setup(
    name='django-service-urls',
    version=service_urls.__version__,
    description='setting helper for django to represent databases, caches and email settings via a single string',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=service_urls.__author__,
    author_email=service_urls.__email__,
    url='https://bitbucket.org/rsalmaso/django-service-urls/',
    download_url='https://bitbucket.org/rsalmaso/django-service-urls/get/{0}.tar.gz'.format(service_urls.__version__),
    license='BSD',
    zip_safe=False,
    python_requires='>=3.5',
    packages=find_packages(exclude=['tests', 'tests.*']),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.1',
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ]
)
