[![Build Status](https://travis-ci.org/delvelabs/hammertime.svg?branch=master)](https://travis-ci.org/delvelabs/hammertime)
[![PyPi](https://badge.fury.io/py/HammerTime-http.svg)](https://badge.fury.io/py/HammerTime-http)
[![Documentation Status](http://readthedocs.org/projects/hammertime/badge/?version=latest)](http://hammertime.readthedocs.io/en/latest/?badge=latest)
![logo](https://raw.githubusercontent.com/delvelabs/hammertime/master/misc/logo.png)

# HammerTime

HammerTime is an HTTP client library aiming to perform a large number of requests
on a server as fast as it can take them, but without distrupting operations
significantly. The primary focus of the library is to support the development of
pentest tools. As such, a set of heuristics are provided to rapidly discard some
requests, filter out invalid responses and generally augment the data available.

## Installation
HammerTime supports 2 simhash libraries: [simhash](https://pypi.org/project/simhash/) and [simhash-py](https://pypi.org/project/simhash-py/).

`pip install hammertime-http[simhash]`

`pip install hammertime-http[simhash-py]`

`pip install hammertime-http` won't have a simhash library and HammerTime won't work correctly.


### !!! Note on installing the `simhash-py` version !!!
The version of simhash-py required isn't released on pypi. It must be installed manually alongside HammerTime, for example by adding it to your `requirements.txt`:

`simhash-py@git+https://github.com/seomoz/simhash-py.git@46de27b310022e3ac7a856c5fc4f4b0df1d76af7`
 

This can't be added to `setup.py` as Pypi will refuse to host a release with a non Pypi dependency. 


## Contributing
Most contributions are welcome. Simply submit a pull request on [GitHub](https://github.com/delvelabs/hammertime/).

Instruction for contributors:
* Accept the contributor license agreement.
* Write tests for your code. Untested code will be rejected.

To report a bug or suggest a feature, open an issue.

## License

Copyright 2016- Delve Labs inc.

This software is published under the GNU General Public License, version 2.

## Logo

HammerTime logo was designed by [Travis Claussen](http://sivartgraphicdesign.com/).
