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
import random

from hammertime.rules import IgnoreLargeBody
from hammertime.http import Entry, StaticResponse
from hammertime.kb import KnowledgeBase


class IgnoreLargeBodyTest(TestCase):

    def setUp(self):
        self.r = IgnoreLargeBody()
        self.r.set_kb(KnowledgeBase())
        self.entry = Entry.create("http://example.om/test", response=StaticResponse(200, {}))

    @async_test()
    async def test_content_length_not_specified(self):
        await self.r.after_headers(self.entry)

        self.assertEqual(self.entry.result.read_length, -1)

    @async_test()
    async def test_receive_length_as_string(self):
        self.entry.response.headers['Content-Length'] = "500"
        await self.r.after_headers(self.entry)

        self.assertIn(500, self.r.data.collected_sizes)
        self.assertEqual(self.entry.result.read_length, self.r.initial_limit)

    @async_test()
    async def test_value_is_not_a_number(self):
        self.entry.response.headers['Content-Length'] = "fivehundred"
        await self.r.after_headers(self.entry)

        self.assertEqual([], self.r.data.collected_sizes)
        self.assertEqual(self.entry.result.read_length, -1)

    @async_test()
    async def test_content_length_below_limit(self):
        self.entry.response.headers['Content-Length'] = self.r.initial_limit / 2
        await self.r.after_headers(self.entry)

        self.assertEqual(self.entry.result.read_length, self.r.initial_limit)

    @async_test()
    async def test_content_length_above_limit(self):
        self.entry.response.headers['Content-Length'] = self.r.initial_limit * 2
        await self.r.after_headers(self.entry)

        self.assertEqual(self.entry.result.read_length, self.r.initial_limit)

        await self.r.after_headers(Entry.create("http://example.om/test",
                                                response=StaticResponse(200, {'Content-Length': self.r.initial_limit * 2})))

    @async_test()
    async def test_content_size_adjusts_over_time(self):
        for _ in range(1000):
            await self.r.after_headers(Entry.create("http://example.om/test",
                                                    response=StaticResponse(200, {'Content-Length': random.randint(10000, 20000)})))

        self.entry.response.headers['Content-Length'] = self.r.initial_limit / 2
        await self.r.after_headers(self.entry)
        self.assertLess(self.entry.result.read_length, self.r.initial_limit)
        self.assertNotEqual(self.entry.result.read_length, -1)

    @async_test()
    async def test_no_not_read_full_once_statistics_are_obtained(self):
        for _ in range(1000):
            await self.r.after_headers(Entry.create("http://example.om/test",
                                                    response=StaticResponse(200, {'Content-Length': random.randint(10000, 20000)})))

        await self.r.after_headers(self.entry)
        self.assertLess(self.entry.result.read_length, self.r.initial_limit)
        self.assertNotEqual(self.entry.result.read_length, -1)

    @async_test()
    async def test_post_response_size_calculation(self):
        self.r.data.initial_limit = 5
        self.entry.response.content = "1234567890"

        await self.r.after_response(self.entry)

        self.assertIn(10, self.r.data.collected_sizes)
        self.assertEqual(self.entry.response.content, "12345")
        self.assertTrue(self.entry.response.truncated)
        self.assertEqual(self.entry.result.read_length, 5)

    @async_test()
    async def test_post_response_calculation_does_not_apply_when_read_size_was_specified(self):
        self.r.data.initial_limit = 5
        self.entry.result.read_length = 5
        self.entry.response.content = "1234567890"

        await self.r.after_response(self.entry)

        self.assertEqual([], self.r.data.collected_sizes)

    @async_test()
    async def test_calculated_limit_is_always_integer(self):
        body_sizes = [43, 26, 79, 32, 97, 54, 81, 33, 29, 103] * 100
        for size in body_sizes:
            response = StaticResponse(200, {'Content-Length': size})
            await self.r.after_headers(Entry.create("http://example.com/", response=response))

        self.assertEqual(self.r.data.calculated_limit, int(self.r.data.calculated_limit))
