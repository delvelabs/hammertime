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
from unittest.mock import MagicMock, call

from fixtures import async_test

from hammertime.rules import RejectStatusCode, DetectFalse404
from hammertime.http import Entry, StaticResponse
from hammertime.ruleset import RejectRequest
from hammertime.engine import Engine


class RejectStatusCodeTest(TestCase):

    @async_test()
    async def test_reject_nothing(self):
        r = RejectStatusCode()
        await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(200, {})))
        await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(302, {})))

    @async_test()
    async def test_do_not_reject_outside_specified_ranges(self):
        r = RejectStatusCode(range(400, 410), range(500, 700))
        await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(200, {})))
        await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(302, {})))
        await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(410, {})))
        await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(460, {})))

    @async_test()
    async def test_do_not_reject_reject_within_the_specified_ranges(self):
        r = RejectStatusCode(range(400, 410), range(500, 700))
        with self.assertRaises(RejectRequest):
            await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(400, {})))

        with self.assertRaises(RejectRequest):
            await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(409, {})))

        with self.assertRaises(RejectRequest):
            await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(503, {})))


class DetectFalse404Test(TestCase):

    def setUp(self):
        self.rule = DetectFalse404()
        self.rule.random_token = "not-so-random"
        self.engine = FakeEngine()
        self.rule.set_engine(self.engine)

    @async_test()
    async def test_calls_made_to_alternate_urls(self):
        await self.rule.after_response(Entry.create("http://example.com/test", response=StaticResponse(400, {})))

        self.engine.mock.perform_high_priority.assert_has_calls([
            call(Entry.create("http://example.com/not-so-random.aspx"), self.rule.child_heuristics),
            call(Entry.create("http://example.com/not-so-random.html"), self.rule.child_heuristics),
        ], any_order=True)

    @async_test()
    async def test_calls_not_made_second_time_around(self):
        await self.rule.after_response(Entry.create("http://example.com/test", response=StaticResponse(400, {})))

        self.engine.mock.reset_mock()

        await self.rule.after_response(Entry.create("http://example.com/test-more-example", response=StaticResponse(400, {})))

        self.engine.mock.perform_high_priority.assert_not_called()


class FakeEngine(Engine):

    def __init__(self):
        self.mock = MagicMock()

    async def perform(self, entry, heuristics):
        return self.mock.perform(entry, heuristics)

    async def perform_high_priority(self, entry, heuristics):
        return self.mock.perform_high_priority(entry, heuristics)
