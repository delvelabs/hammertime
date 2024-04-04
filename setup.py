#!/usr/bin/env python

from setuptools import setup


version_file = "hammertime/__version__.py"
version_data = {}
with open(version_file) as f:
    code = compile(f.read(), version_file, 'exec')
    exec(code, globals(), version_data)

setup(name='HammerTime-http',
      version=version_data['__version__'],
      description='HammerTime is an HTTP client library aiming to perform a large number of requests on a server as fast as it can take them, but without distrupting operations significantly.',
      python_requires='>=3.8.0,<4',
      author='Delve Labs inc.',
      author_email='info@delvelabs.ca',
      url='https://github.com/delvelabs/hammertime',
      packages=['hammertime',
                'hammertime.engine',
                'hammertime.rules',
                'hammertime.utils'],
      install_requires=[
        'aiodns>=1.1.1,<3.0.0',
        'aiohttp>=3.7.3,<4.0.0',
        'easyinject>=0.3,<0.4',
        'marshmallow-autoschema>=0.4.0,<0.5.0',
        'marshmallow-har>=1.2.0,<1.3.0',
      ],
      setup_requires=["pytest-runner"],
      tests_require=[
        'async_timeout>=4.0.2,<5.0.0',
        'coverage',
        'flake8>=3.8.4,<4.0.0',
        'pytest>=6.0',
        'simhash==2.1.2',
      ],
      license="GPLv2",
      )
