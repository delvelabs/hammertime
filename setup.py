#!/usr/bin/env python

from setuptools import setup

setup(name='HammerTime-http',
      version='0.1.1',
      description='HammerTime is an HTTP client library aiming to perform a large number of requests on a server as fast as it can take them, but without distrupting operations significantly.',
      author='Delve Labs inc.',
      author_email='info@delvelabs.ca',
      url='https://github.com/delvelabs/hammertime',
      packages=['hammertime',
                'hammertime.engine',
                'hammertime.rules'],
      install_requires=[
          'aiohttp',
          'async_timeout',
          'easyinject',
          'simhash',
      ],
      license="GPLv2"
     )
