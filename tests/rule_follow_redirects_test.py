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
from copy import copy
from aiohttp.test_utils import make_mocked_coro

from hammertime.rules import FollowRedirects
from fixtures import async_test
from hammertime.http import Entry, StaticResponse as Response
from hammertime.ruleset import StopRequest, RejectRequest


class TestFollowRedirects(TestCase):

    def setUp(self):
        self.engine = FakeEngine()
        self.rule = FollowRedirects(max_redirect=10)
        self.rule.set_engine(self.engine)
        self.response = Response(code=302, headers={"location": "https://www.example.com/"})
        self.response.set_content(b"", at_eof=True)
        self.entry = Entry.create("http://example.com", response=self.response)

    @async_test()
    async def test_on_request_successful_ignore_response_if_not_redirect(self):
        response = MagicMock(code=200, headers={})
        entry = Entry.create("http://example.com", response=response)

        await self.rule.on_request_successful(entry)

        self.engine.mock.assert_not_called()

    @async_test()
    async def test_on_request_successful_perform_new_request_for_redirect(self):
        final_response = MagicMock(code=200, headers={})
        self.engine.response = final_response

        await self.rule.on_request_successful(self.entry)

        self.engine.mock.assert_called_once_with(Entry.create("https://www.example.com/", response=final_response),
                                                 self.rule.child_heuristics)

    @async_test()
    async def test_on_request_successful_keep_initial_request(self):
        initial_request = self.entry.request
        final_response = MagicMock(code=200, headers={})
        self.engine.response = final_response

        await self.rule.on_request_successful(self.entry)

        self.assertEqual(self.entry.request, initial_request)

    @async_test()
    async def test_on_request_successful_set_final_response_as_entry_response(self):
        final_response = Response(code=200, headers={})
        final_response.set_content(b"data", at_eof=True)
        self.engine.response = final_response

        await self.rule.on_request_successful(self.entry)

        self.assertEqual(self.entry.response, final_response)

    @async_test()
    async def test_on_request_successful_store_intermediate_entry_in_result(self):
        response = copy(self.response)
        final_response = Response(code=200, headers={})
        final_response.set_content(b"response content", at_eof=True)
        self.engine.response = final_response

        await self.rule.on_request_successful(self.entry)

        expected = [Entry.create(self.entry.request.url, method=self.entry.request.method,
                                 headers=self.entry.request.headers, response=response),
                    Entry.create("https://www.example.com/", method='GET', headers={}, response=final_response)]
        self.assertEqual(self.entry.result.redirects, expected)

    @async_test()
    async def test_on_request_successful_raise_reject_request_if_max_redirect_limit_reached(self):
        self.engine.response = Response(code=302, headers={"location": "http://example.com/"})
        self.engine.response.set_content(b"data", at_eof=True)

        with self.assertRaises(RejectRequest):
            await self.rule.on_request_successful(self.entry)

            self.assertEqual(self.engine.mock.call_count, self.rule.max_redirect)
            self.assertEqual(len(self.entry.result.redirects), self.rule.max_redirect + 1)

    @async_test()
    async def test_on_request_successful_increment_stats_for_each_redirect(self):
        final_response = Response(code=200, headers={})
        final_response.set_content(b"response content", at_eof=True)
        self.engine.response = final_response

        await self.rule.on_request_successful(self.entry)

        self.assertEqual(self.engine.stats.requested, 2)
        self.assertEqual(self.engine.stats.completed, 1)

    @async_test()
    async def test_on_request_successful_reject_request_if_no_location_in_response_header(self):
        self.engine.response = Response(code=302, headers={})
        self.engine.response.set_content(b"data", at_eof=True)

        with self.assertRaises(RejectRequest):
            await self.rule.on_request_successful(self.entry)

    @async_test()
    async def test_relative_path_in_location(self):
        self.engine.mock.side_effect = [
            Response(code=302, headers={"location": "splash/index.html"}),
            Response(code=201, headers={}),
        ]

        await self.rule.on_request_successful(self.entry)

        self.assertEqual(201, self.entry.response.code)
        self.assertEqual("https://www.example.com/splash/index.html", self.entry.result.redirects[-1].request.url)

    @async_test()
    async def test_relative_path_with_mutliple_redirects(self):
        self.engine.mock.side_effect = [
            Response(code=302, headers={"location": "splash/index.html"}),
            Response(code=302, headers={"location": "index.php"}),
            Response(code=201, headers={}),
        ]

        await self.rule.on_request_successful(self.entry)

        self.assertEqual(201, self.entry.response.code)
        self.assertEqual("https://www.example.com/splash/index.php", self.entry.result.redirects[-1].request.url)

    @async_test()
    async def test_path_absolute(self):
        self.engine.mock.side_effect = [
            Response(code=302, headers={"location": "splash/index.html"}),
            Response(code=302, headers={"location": "/index.php"}),
            Response(code=201, headers={}),
        ]

        await self.rule.on_request_successful(self.entry)

        self.assertEqual(201, self.entry.response.code)
        self.assertEqual("https://www.example.com/index.php", self.entry.result.redirects[-1].request.url)

    @async_test()
    async def test_full_different_domain(self):
        self.engine.mock.side_effect = [
            Response(code=302, headers={"location": "http://example.org/splash/index.html"}),
            Response(code=302, headers={"location": "test"}),
            Response(code=201, headers={}),
        ]

        await self.rule.on_request_successful(self.entry)

        self.assertEqual(201, self.entry.response.code)
        self.assertEqual("http://example.org/splash/test", self.entry.result.redirects[-1].request.url)

    @async_test()
    async def test_on_request_successful_raise_exception_if_redirect_fail(self):
        engine = MagicMock()
        engine.perform = make_mocked_coro(raise_exception=StopRequest())
        self.rule.set_engine(engine)

        with self.assertRaises(StopRequest):
            await self.rule.on_request_successful(self.entry)


class FakeEngine:

    def __init__(self):
        self.response = None
        self.mock = MagicMock()
        self.stats = MagicMock(requested=1, completed=0)

    async def perform(self, entry, heuristics=None):
        entry.response = self.mock(entry, heuristics)
        if self.response is not None:
            entry.response = self.response
        return entry
