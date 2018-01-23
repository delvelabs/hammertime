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

import asyncio
from async_timeout import timeout

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientOSError, ClientResponseError, ServerDisconnectedError
from aiohttp.connector import TCPConnector
import ssl

from ..ruleset import StopRequest, RejectRequest


class AioHttpEngine:

    def __init__(self, *, loop, verify_ssl=True, ca_certificate_file=None, proxy=None, timeout=0.2):
        self.loop = loop
        ssl_context = None
        if ca_certificate_file is not None:
            ssl_context = ssl.create_default_context()
            ssl_context.load_verify_locations(cafile=ca_certificate_file)
        connector = TCPConnector(loop=loop, verify_ssl=verify_ssl, ssl_context=ssl_context)
        self.session = ClientSession(loop=loop, connector=connector)
        self.proxy = proxy
        self.timeout = timeout

    async def perform(self, entry, heuristics):
        try:
            await heuristics.before_request(entry)
            return await self._perform(entry, heuristics)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            await heuristics.on_timeout(entry)
            raise StopRequest("Timeout reached")
        except ClientOSError:
            await heuristics.on_host_unreachable(entry)
            raise StopRequest("Host Unreachable")
        except ClientResponseError:
            raise StopRequest("Connection Error")
        except ServerDisconnectedError:
            raise StopRequest("Server Disconnected")
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
                                                  timeout=timeout_value, **extra_args)

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
        self.session.close()

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
            raise ValueError("Content is only partially read")

        return self.raw.decode('utf-8')

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __copy__(self):
        response = Response(self.code, self.headers)
        response.set_content(self.raw, not self.truncated)
        return response
