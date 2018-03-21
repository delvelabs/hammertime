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


from copy import copy


class Entry:

    def __init__(self, request, response, result, arguments):
        self.request = request
        self.response = response
        self.result = result
        self.arguments = arguments

    @staticmethod
    def create(*args, response=None, arguments=None, **kwargs):
        return Entry(request=Request(*args, **kwargs), response=response, result=Result(), arguments=arguments or {})

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __copy__(self):
        return Entry(request=copy(self.request), response=copy(self.response), result=copy(self.result),
                     arguments=copy(self.arguments))


class Request:

    def __init__(self, url, *, method='GET', headers=None):
        self.method = method
        self.url = url
        self.headers = headers or {}

    def __hash__(self):
        return hash(self.__dict__)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return "Request(%s %s)" % (self.method, self.url)

    def __copy__(self):
        return Request(self.url, method=self.method, headers=copy(self.headers))


class Result:
    def __init__(self):
        self.attempt = 1
        self.read_length = -1  # -1 is unlimited
        self.redirects = []

    def __hash__(self):
        return hash(self.__dict__)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __copy__(self):
        _copy = Result()
        _copy.attempt = self.attempt
        _copy.read_length = self.read_length
        _copy.redirects = copy(self.redirects)
        return _copy

    def __repr__(self):
        return repr(self.__dict__)


class StaticResponse:

    def __init__(self, code, headers, content=None):
        self.code = code
        self.headers = headers
        self.content = content
        self.truncated = False

    def set_content(self, data, at_eof):
        self.raw = data
        self.truncated = not at_eof

    @property
    def raw(self):
        return self.content.encode('utf-8')

    @raw.setter
    def raw(self, value):
        self.content = value.decode('utf-8')

    @property
    def partial_content(self):
        return self.content

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __copy__(self):
        return StaticResponse(self.code, copy(self.headers), content=self.content)
