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


from aiohttp import ClientSession
from aiohttp import ClientSSLError
from aiohttp.client_exceptions import ClientOSError, ClientResponseError, ServerDisconnectedError, ClientError
from aiohttp.cookiejar import DummyCookieJar
import asyncio
from async_timeout import timeout
import ssl

from ..ruleset import StopRequest, RejectRequest


class AioHttpEngine:

    def __init__(self, *, loop, verify_ssl=True, ca_certificate_file=None, proxy=None, timeout=0.2,
                 disable_cookies=False, client_session=None):
        self.loop = loop
        self.session = client_session
        if self.session is None:
            if disable_cookies:
                self.session = ClientSession(loop=loop, cookie_jar=DummyCookieJar(loop=loop))
            else:
                self.session = ClientSession(loop=loop)
        self.proxy = proxy
        self.timeout = timeout
        self.ssl = None
        self.set_ssl_parameters(verify_ssl=verify_ssl, ca_certificate_file=ca_certificate_file)

    def set_ssl_parameters(self, *, verify_ssl=True, ca_certificate_file=None):
        if ca_certificate_file:
            self.ssl = ssl.create_default_context(cafile=ca_certificate_file)
        elif not verify_ssl:
            self.ssl = verify_ssl
        else:
            self.ssl = None

    async def perform(self, entry, heuristics):
        try:
            await heuristics.before_request(entry)
            return await self._perform(entry, heuristics)
        except asyncio.TimeoutError:
            await heuristics.on_timeout(entry)
            raise StopRequest("Timeout reached")
        except ClientSSLError:
            raise StopRequest("SSL Error")
        except ClientOSError:
            await heuristics.on_host_unreachable(entry)
            raise StopRequest("Host Unreachable")
        except ClientResponseError:
            raise StopRequest("Connection Error")
        except ServerDisconnectedError:
            raise StopRequest("Server Disconnected")
        except ClientError as e:
            raise StopRequest(str(e))
        # If request is cancelled, it raises a KeyError. If session is closed, session.request raises a RuntimeError.
        except (KeyError, RuntimeError, asyncio.CancelledError):
            raise asyncio.CancelledError

    async def _perform(self, entry, heuristics):
        req = entry.request

        timeout_value = entry.arguments.get("timeout", self.timeout)
        with timeout(timeout_value + 0.3, loop=self.loop):
            extra_args = {}
            if self.proxy:
                extra_args["proxy"] = self.proxy
            if entry.request.headers:
                extra_args["headers"] = entry.request.headers

            response = await self.session.request(method=req.method, url=req.url, allow_redirects=False,
                                                  timeout=timeout_value, ssl=self.ssl, **extra_args)

        # When the request is simply rejected, we want to keep the persistent connection alive
        async with ProtectedSession(response, RejectRequest):
            entry.response = Response(response.status, response.headers)

            await heuristics.after_headers(entry)

            with timeout(2.0):
                # read_length is set to -1 if unlimited, which is the same as aiohttp
                max_length = entry.result.read_length
                entry.response.set_content(await response.content.read(max_length), response.content.at_eof())

        await heuristics.after_response(entry)

        return entry

    async def close(self):
        await self.session.close()

    def set_proxy(self, proxy):
        self.proxy = proxy


class ProtectedSession:
    """
    Make sure the parent context closes properly even if a certain type
    of exception is raised.
    """

    def __init__(self, context, exception_class):
        self.context = context
        self.exception_class = exception_class

    async def __aenter__(self):
        await self.context.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type == self.exception_class:
            # Read content before releasing response to keep its connection alive.
            await self.context.read()
            # Simple release
            await self.context.__aexit__(None, None, None)
        else:
            # Close
            await self.context.__aexit__(exc_type, exc, tb)


class Response:

    def __init__(self, status, headers):
        self.code = status
        self.headers = headers

    def set_content(self, data, at_eof):
        self.raw = data
        self.truncated = not at_eof

    @property
    def content(self):
        if self.truncated:
            return self.partial_content
        else:
            return self.raw.decode('utf-8')

    @property
    def partial_content(self):
        try:
            return self.raw.decode("utf-8")
        except UnicodeDecodeError as decode_error:
            longest_bytes_sequence_in_utf8 = 4
            if decode_error.start >= len(self.raw) - longest_bytes_sequence_in_utf8:
                # ignore error due the the last character sequence being truncated, content is still valid utf-8.
                return self.raw.decode("utf-8", errors="ignore")
            else:
                raise decode_error

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __copy__(self):
        response = Response(self.code, self.headers)
        response.set_content(self.raw, not self.truncated)
        return response
