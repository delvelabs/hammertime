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

from hammertime.rules import FollowRedirects
from fixtures import async_test
from hammertime.http import Entry, Request
from hammertime.engine.aiohttp import Response


class TestFollowRedirects(TestCase):

    def setUp(self):
        self.engine = FakeEngine()
        self.rule = FollowRedirects(max_redirect=10)
        self.rule.set_engine(self.engine)

    @async_test()
    async def test_after_headers_ignore_response_if_not_redirect(self):
        response = MagicMock(code=200, headers={})
        entry = Entry.create("http://example.com", response=response)

        await self.rule.after_headers(entry)

        self.engine.mock.assert_not_called()

    @async_test()
    async def test_after_headers_create_new_request_for_redirect(self):
        response = MagicMock(code=302, headers={"location": "https://www.example.com/"})
        entry = Entry.create("http://example.com", response=response)
        final_response = MagicMock(code=200, headers={})
        self.engine.response = final_response

        await self.rule.after_headers(entry)

        self.engine.mock.assert_called_once_with(Entry.create("https://www.example.com/"), self.rule.child_heuristics)

    @async_test()
    async def test_after_headers_keep_initial_request(self):
        response = MagicMock(code=302, headers={"location": "https://www.example.com/"})
        entry = Entry.create("http://example.com", response=response)
        initial_request = entry.request
        final_response = MagicMock(code=200, headers={})
        self.engine.response = final_response

        await self.rule.after_headers(entry)

        self.assertEqual(entry.request, initial_request)

    @async_test()
    async def test_after_headers_set_final_response_as_entry_response(self):
        response = Response(status=302, headers={"location": "https://www.example.com/"})
        response.set_content(b"", at_eof=True)
        entry = Entry.create("http://example.com", response=response)
        final_response = Response(status=200, headers={})
        final_response.set_content(b"data", at_eof=True)
        self.engine.response = final_response

        await self.rule.after_headers(entry)

        self.assertEqual(entry.response, final_response)

    @async_test()
    async def test_after_headers_store_intermediate_requests_and_responses_in_result(self):
        response = Response(status=302, headers={"location": "https://www.example.com/"})
        response.set_content(b"content", at_eof=True)
        entry = Entry.create("http://example.com", response=copy(response))
        final_response = Response(status=200, headers={})
        final_response.set_content(b"response content", at_eof=True)
        self.engine.response = final_response

        await self.rule.after_headers(entry)

        self.assertEqual(entry.result.redirects, [(entry.request, response),
                                                  (Request("https://www.example.com/"), final_response)])

    @async_test()
    async def test_after_headers_dont_follow_redirect_if_max_redirect_limit_reached(self):
        response = MagicMock(code=302, headers={"location": "http://example.com/"})
        entry = Entry.create("http://example.com", response=response)
        self.engine.response = MagicMock(code=302, headers={"location": "http://example.com/"})

        await self.rule.after_headers(entry)

        self.assertEqual(self.engine.mock.call_count, self.rule.max_redirect)
        self.assertEqual(len(entry.result.redirects), self.rule.max_redirect + 1)


class FakeEngine:

    def __init__(self):
        self.response = None
        self.mock = MagicMock()

    async def perform_high_priority(self, entry, heuristics=None):
        self.mock(entry, heuristics)
        if self.response is not None:
            return entry._replace(response=self.response)
        return entry
