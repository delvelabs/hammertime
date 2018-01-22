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
from hammertime.rules import DeadHostDetection
from hammertime.kb import KnowledgeBase
from hammertime.http import Entry
from hammertime.rules.deadhostdetection import OfflineHostException


class TestDeadHostDetection(TestCase):

    def setUp(self):
        self.dead_host_detection = DeadHostDetection()
        self.kb = KnowledgeBase()
        self.dead_host_detection.set_kb(self.kb)

    @async_test()
    async def test_before_request_init_host_state(self):
        entry = Entry.create("http://example.com/test")

        await self.dead_host_detection.before_request(entry)

        self.assertEqual(self.dead_host_detection.hosts["example.com"]["timeout_requests"], 0)

    @async_test()
    async def test_before_request_raise_offline_host_exception_if_host_is_offline(self):
        entry = Entry.create("http://example.com/")
        await self.dead_host_detection.before_request(entry)
        self.dead_host_detection.dead_hosts = ["example.com"]

        with self.assertRaises(OfflineHostException):
            await self.dead_host_detection.before_request(entry)

    @async_test()
    async def test_after_headers_reset_timeout_requests(self):
        self.dead_host_detection.hosts["example.com"] = {"timeout_requests": 10}

        await self.dead_host_detection.after_headers(Entry.create("http://example.com/"))

        self.assertEqual(self.dead_host_detection.hosts["example.com"]["timeout_requests"], 0)

    @async_test()
    async def test_on_timeout_increment_timeout_requests_for_host(self):
        await self.dead_host_detection.before_request(Entry.create("http://example.com/"))
        await self.dead_host_detection.before_request(Entry.create("http://www.test.com/"))
        await self.dead_host_detection.before_request(Entry.create("http://10.10.10.10:8080/"))

        await self.dead_host_detection.on_timeout(Entry.create("http://example.com/"))
        await self.dead_host_detection.on_timeout(Entry.create("http://example.com/"))

        await self.dead_host_detection.on_timeout(Entry.create("http://www.test.com/"))

        await self.dead_host_detection.on_timeout(Entry.create("http://10.10.10.10:8080/"))
        await self.dead_host_detection.on_timeout(Entry.create("http://10.10.10.10:8080/"))
        await self.dead_host_detection.on_timeout(Entry.create("http://10.10.10.10:8080/"))

        self.assertEqual(self.dead_host_detection.hosts["example.com"]["timeout_requests"], 2)
        self.assertEqual(self.dead_host_detection.hosts["www.test.com"]["timeout_requests"], 1)
        self.assertEqual(self.dead_host_detection.hosts["10.10.10.10:8080"]["timeout_requests"], 3)

    @async_test()
    async def test_on_timeout_raise_offline_host_exception_if_timeout_requests_exceed_threshold(self):
        self.dead_host_detection.threshold = 2
        entry = Entry.create("http://example.com/")
        await self.dead_host_detection.before_request(entry)

        await self.dead_host_detection.on_timeout(entry)  # only 1 request have timed out, no exception should be raised

        with self.assertRaises(OfflineHostException):
            await self.dead_host_detection.on_timeout(entry)

    @async_test()
    async def test_on_timeout_add_dead_host_to_dead_host_list(self):
        entry = Entry.create("http://example.com/")
        self.dead_host_detection.hosts["example.com"] = {"timeout_requests": self.dead_host_detection.threshold}

        try:
            await self.dead_host_detection.on_timeout(entry)
        except OfflineHostException:
            pass

        self.assertIn("example.com", self.kb.dead_hosts)

    @async_test()
    async def test_on_error_reset_timeout_requests_count(self):
        entry = Entry.create("http://example.com/")
        self.dead_host_detection.hosts["example.com"] = {"timeout_requests": 50}

        await self.dead_host_detection.on_error(entry)

        self.assertEqual(self.dead_host_detection.hosts["example.com"]["timeout_requests"], 0)
