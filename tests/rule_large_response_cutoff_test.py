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
from hammertime.ruleset import IgnoreBody
from hammertime.kb import KnowledgeBase


class IgnoreLargeBodyTest(TestCase):

    def setUp(self):
        self.r = IgnoreLargeBody()
        self.r.set_kb(KnowledgeBase())

    @async_test()
    async def test_content_length_not_specified(self):
        await self.r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(200, {})))

    @async_test()
    async def test_receive_length_as_string(self):
        await self.r.after_headers(Entry.create("http://example.om/test",
                                                response=StaticResponse(200, {'Content-Length': "500"})))
        self.assertIn(500, self.r.data.collected_sizes)

    @async_test()
    async def test_value_is_not_a_number(self):
        await self.r.after_headers(Entry.create("http://example.om/test",
                                                response=StaticResponse(200, {'Content-Length': "fivehundred"})))
        self.assertEqual([], self.r.data.collected_sizes)

    @async_test()
    async def test_content_length_defined(self):
        await self.r.after_headers(Entry.create("http://example.om/test",
                                                response=StaticResponse(200, {'Content-Length': self.r.initial_limit / 2})))

        with self.assertRaises(IgnoreBody):
            await self.r.after_headers(Entry.create("http://example.om/test",
                                                    response=StaticResponse(200, {'Content-Length': self.r.initial_limit * 2})))

    @async_test()
    async def test_content_size_adjusts_over_time(self):
        for _ in range(1000):
            await self.r.after_headers(Entry.create("http://example.om/test",
                                                    response=StaticResponse(200, {'Content-Length': random.randint(10000, 20000)})))

        with self.assertRaises(IgnoreBody):
            await self.r.after_headers(Entry.create("http://example.om/test",
                                                    response=StaticResponse(200, {'Content-Length': self.r.initial_limit / 2})))
