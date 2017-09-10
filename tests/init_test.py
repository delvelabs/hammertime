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

from unittest import TestCase
from unittest.mock import MagicMock
from fixtures import async_test

from hammertime.core import HammerTime
from hammertime.engine import Engine
from hammertime.http import StaticResponse
from hammertime.ruleset import StopRequest, RejectRequest
from hammertime.rules import RejectStatusCode
from hammertime.engine.aiohttp import AioHttpEngine
import asyncio
from aiohttp.test_utils import make_mocked_coro
import async_timeout


class InitTest(TestCase):

    @async_test()
    async def test_open_and_close(self, loop):
        h = HammerTime(loop=loop)
        await h.close()

        self.assertEqual(h.completed_count, 0)

    @async_test()
    async def test_add_requests_and_wait_for_completion(self, loop):
        h = HammerTime(loop=loop, request_engine=FakeEngine())
        entry = await h.request("http://example.com")
        self.assertEqual(entry.response.content, "http://example.com")
        await h.close()

    @async_test()
    async def test_preserve_arguments(self, loop):
        h = HammerTime(loop=loop, request_engine=FakeEngine())
        entry = await h.request("http://example.com", arguments={"hello": "world"})
        self.assertEqual(entry.arguments["hello"], "world")

    @async_test()
    async def test_wait_for_multiple_requests(self, loop):
        h = HammerTime(loop=loop, request_engine=FakeEngine())
        promise_1 = h.request("http://example.com/1")
        promise_2 = h.request("http://example.com/2")

        entry = await promise_2
        self.assertEqual(entry.response.content, "http://example.com/2")

        entry = await promise_1
        self.assertEqual(entry.response.content, "http://example.com/1")
        await h.close()

        self.assertEqual(h.completed_count, 2)

    @async_test()
    async def test_loop_over_results(self, loop):
        h = HammerTime(loop=loop, request_engine=FakeEngine())
        h.request("http://example.com/1")
        h.request("http://example.com/2")

        out = set()

        async for entry in h.successful_requests():
            out.add(entry.response.content)

        self.assertEqual(out, {"http://example.com/1", "http://example.com/2"})
        self.assertEqual(h.completed_count, 2)

    @async_test()
    async def test_successive_loop_over_results(self, loop):
        h = HammerTime(loop=loop, request_engine=FakeEngine())
        h.request("http://example.com/1")
        h.request("http://example.com/2")
        out = set()

        async for entry in h.successful_requests():
            out.add(entry.response.content)

        h.request("http://example.com/3")
        h.request("http://example.com/4")

        async for entry in h.successful_requests():
            out.add(entry.response.content)

        self.assertEqual(out, {"http://example.com/1", "http://example.com/2", "http://example.com/3",
                               "http://example.com/4"})
        self.assertEqual(h.completed_count, 4)

    @async_test()
    async def test_skip_results_that_fail(self, loop):
        h = HammerTime(loop=loop, request_engine=FakeEngine())
        h.heuristics.add(BlockRequest("http://example.com/1"))
        h.request("http://example.com/1")
        h.request("http://example.com/2")

        out = set()

        async for entry in h.successful_requests():
            out.add(entry.response.content)

        self.assertEqual(out, {"http://example.com/2"})
        self.assertEqual(h.completed_count, 2)

    @async_test()
    async def test_successful_requests_return_if_no_pending_requests(self, loop):
        h = HammerTime(loop=loop, request_engine=FakeEngine())

        try:
            with async_timeout.timeout(0.001):
                async for entry in h.successful_requests():
                    pass
        except asyncio.TimeoutError:
            self.fail("Function blocked.")

    @async_test()
    async def test_provide_exception_when_resolving_specific_promise(self, loop):
        h = HammerTime(loop=loop, request_engine=FakeEngine())
        h.heuristics.add(BlockRequest("http://example.com/1"))
        future = h.request("http://example.com/1")

        with self.assertRaises(StopRequest):
            await future

        with self.assertRaises(StopRequest):
            await future

    @async_test()
    async def test_explicit_abandon_obtained_when_requested(self, loop):
        h = HammerTime(loop=loop, request_engine=FakeEngine(), retry_count=2)
        h.heuristics.add(RejectStatusCode(range(0, 600)))  # Everything
        future = h.request("http://example.com/1")

        with self.assertRaises(RejectRequest):
            await future

        self.assertEqual(0, h.stats.retries)

    @async_test()
    async def test_retries_performed_and_response_obtained(self, loop):
        h = HammerTime(loop=loop, request_engine=FakeEngine(), retry_count=2)
        h.heuristics.add(BlockRequest("http://example.com/1"))
        entry = await h.request("http://example.com/1")

        self.assertEqual(entry.response.content, "http://example.com/1")

    @async_test()
    async def test_constructor_set_aiohttp_engine_proxy_if_constructor_proxy_is_not_none(self, loop):
        h = HammerTime(loop=loop, request_engine=MagicMock(), proxy="http://some.proxy.com/")

        aiohttp_engine = h.request_engine.request_engine

        aiohttp_engine.set_proxy.assert_called_once_with("http://some.proxy.com/")

    @async_test()
    async def test_constructor_do_not_overwrite_aiohttp_engine_proxy_if_constructor_proxy_is_none(self, loop):
        engine = AioHttpEngine(loop=loop, proxy="http://some.proxy.com")
        h = HammerTime(loop=loop, request_engine=engine)

        aiohttp_engine = h.request_engine.request_engine

        self.assertEqual(aiohttp_engine.proxy, "http://some.proxy.com")

    @async_test()
    async def test_set_proxy_set_aiohttp_engine_proxy(self, loop):
        h = HammerTime(loop=loop, request_engine=MagicMock())

        h.set_proxy("http://some.proxy.com/")

        aiohttp_engine = h.request_engine.request_engine
        aiohttp_engine.set_proxy.assert_called_with("http://some.proxy.com/")

    @async_test()
    async def test_no_successful_request_returned_when_requests_are_cancelled(self, loop):
        engine = MagicMock()
        engine.perform = make_mocked_coro(raise_exception=asyncio.CancelledError)
        hammertime = HammerTime(loop=loop, request_engine=engine)

        for i in range(5):
            hammertime.request("http://example.com")

        successful_requests = []
        async for request in hammertime.successful_requests():
            successful_requests.append(request)

        self.assertEqual(successful_requests, [])

    @async_test()
    async def test_request_raise_cancelled_error_if_hammertime_is_close(self, loop):
        hammertime = HammerTime(loop=loop)

        await hammertime.close()

        self.assertTrue(hammertime.is_closed)
        with self.assertRaises(asyncio.CancelledError):
            hammertime.request("http://example.com")

    @async_test()
    async def test_interrupt_close_hammertime(self, loop):
        hammertime = HammerTime(loop=loop)

        hammertime._interrupt()
        # Wait for hammertime.close to be called.
        await hammertime.closed

        self.assertTrue(hammertime.is_closed)


class FakeEngine(Engine):

    async def perform(self, entry, heuristics):
        await heuristics.before_request(entry)
        entry = entry._replace(response=StaticResponse(200, {"Content-Type": "text/junk"}))
        await heuristics.after_headers(entry)
        entry.response.content = entry.request.url
        await heuristics.after_response(entry)

        return entry

    def set_proxy(self, proxy):
        pass


class BlockRequest:
    def __init__(self, url):
        self.url = url

    async def before_request(self, entry):
        if entry.request.url == self.url and entry.result.attempt < 3:
            raise StopRequest()
