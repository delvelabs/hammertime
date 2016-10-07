# hammertime: A high-volume http fetch library
# Copyright (C) 2016-  Delve Labs inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from collections import namedtuple


Entry = namedtuple('Entry', ['request', 'response', 'result'])
Entry.create = lambda *args, **kwargs: Entry(request=Request(*args, **kwargs), response=None, result=Result())


class Request:

    def __init__(self, url, *, method='GET'):
        self.method = method
        self.url = url


class Result:
    def __init__(self):
        self.attempt = 1


class StaticResponse:

    def __init__(self, code, headers, content=None):
        self.code = code
        self.headers = headers
        self.content = content
