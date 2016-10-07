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
from fixtures import async_test

from hammertime.core import HammerTime
from hammertime.engine import Engine
from hammertime.http import StaticResponse
from hammertime.ruleset import StopRequest


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
    async def test_provide_exception_when_resolving_specific_promise(self, loop):
        h = HammerTime(loop=loop, request_engine=FakeEngine())
        h.heuristics.add(BlockRequest("http://example.com/1"))
        future = h.request("http://example.com/1")

        with self.assertRaises(StopRequest):
            await future

        with self.assertRaises(StopRequest):
            await future

    @async_test()
    async def test_retries_performed_and_response_obtained(self, loop):
        h = HammerTime(loop=loop, request_engine=FakeEngine(), retry_count=2)
        h.heuristics.add(BlockRequest("http://example.com/1"))
        _, resp, result = await h.request("http://example.com/1")

        self.assertEqual(resp.content, "http://example.com/1")


class FakeEngine(Engine):

    async def perform(self, entry, heuristics):
        await heuristics.before_request(entry)
        entry = entry._replace(response=StaticResponse(200, {"Content-Type": "text/junk"}))
        await heuristics.after_headers(entry)
        entry.response.content = entry.request.url
        await heuristics.after_response(entry)

        return entry


class BlockRequest:
    def __init__(self, url):
        self.url = url

    async def before_request(self, entry):
        if entry.request.url == self.url and entry.result.attempt < 3:
            raise StopRequest()
