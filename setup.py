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
      author='Delve Labs inc.',
      author_email='info@delvelabs.ca',
      url='https://github.com/delvelabs/hammertime',
      packages=['hammertime',
                'hammertime.engine',
                'hammertime.rules'],
      install_requires=[
          'aiohttp>=3.1.0,<3.3.0',
          'easyinject==0.3',
          'aiodns>=1.1.1,<1.2.0',
          'simhash>=1.8.0,<1.9.0'
      ],
      license="GPLv2"
     )
