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
import asyncio
from aiohttp.test_utils import make_mocked_coro

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
    async def test_before_attempt_increment_request_count_for_host(self):
        netloc0 = "example.com"
        netloc1 = "www.test.example"
        netloc2 = "10.0.0.10:8080"

        await self.dead_host_detection.before_attempt(Entry.create("http://example.com/test"))
        await self.dead_host_detection.before_attempt(Entry.create("http://example.com/12"))

        await self.dead_host_detection.before_attempt(Entry.create("http://www.test.example/index.html"))

        await self.dead_host_detection.before_attempt(Entry.create("http://10.0.0.10:8080/qw"))
        await self.dead_host_detection.before_attempt(Entry.create("http://10.0.0.10:8080/we"))
        await self.dead_host_detection.before_attempt(Entry.create("http://10.0.0.10:8080/rt"))

        self.assertEqual(self.dead_host_detection.hosts[netloc0]["request_count"], 2)
        self.assertEqual(self.dead_host_detection.hosts[netloc1]["request_count"], 1)
        self.assertEqual(self.dead_host_detection.hosts[netloc2]["request_count"], 3)

    @async_test()
    async def test_before_attempt_set_new_host_as_possibly_dead(self):
        entry = Entry.create("http://example.com/")

        await self.dead_host_detection.before_attempt(entry)

        self.assertTrue(self.dead_host_detection.hosts["example.com"]["possibly_dead"])

    @async_test()
    async def test_before_attempt_does_not_increment_request_count_if_host_not_possibly_dead(self):
        self.dead_host_detection.hosts["example.com"] = {"possibly_dead": False, "request_count": 0}

        await self.dead_host_detection.before_attempt(Entry.create("http://example.com/"))

        self.assertEqual(self.dead_host_detection.hosts["example.com"]["request_count"], 0)

    @async_test()
    async def test_before_attempt_sleep_before_retries_if_host_possibly_dead(self):
        entry = Entry.create("http://example.com/")
        entry.result.attempt = 2
        self.dead_host_detection.hosts["example.com"] = {"request_count": 1, "possibly_dead": True}
        asyncio.sleep = make_mocked_coro()

        await self.dead_host_detection.before_attempt(entry)

        asyncio.sleep.assert_called_once_with(self.dead_host_detection.wait_time)

    @async_test()
    async def test_before_attempt_raise_offline_host_exception_if_host_is_dead(self):
        entry = Entry.create("http://example.com/")
        entry.result.attempt = 2
        self.dead_host_detection.hosts["example.com"] = {"request_count": 1, "possibly_dead": True}
        self.dead_host_detection.dead_hosts = ["example.com"]

        with self.assertRaises(OfflineHostException):
            await self.dead_host_detection.before_attempt(entry)

    @async_test()
    async def test_after_headers_set_possibly_dead_to_false_and_reset_state(self):
        self.dead_host_detection.hosts["example.com"] = \
            {"request_count": 2, "possibly_dead": True, "timeout_requests": 1}
        self.dead_host_detection.hosts["www.test.com"] = \
            {"request_count": 1, "possibly_dead": True, "timeout_requests": 1}
        self.dead_host_detection.hosts["10.11.12.13:8080"] = \
            {"request_count": 3, "possibly_dead": True, "timeout_requests": 2}

        await self.dead_host_detection.after_headers(Entry.create("http://example.com/"))
        await self.dead_host_detection.after_headers(Entry.create("http://www.test.com/"))
        await self.dead_host_detection.after_headers(Entry.create("http://10.11.12.13:8080/"))

        self.assertEqual(self.dead_host_detection.hosts["example.com"]["request_count"], 0)
        self.assertEqual(self.dead_host_detection.hosts["example.com"]["timeout_requests"], 0)
        self.assertFalse(self.dead_host_detection.hosts["example.com"]["possibly_dead"])
        self.assertEqual(self.dead_host_detection.hosts["www.test.com"]["request_count"], 0)
        self.assertEqual(self.dead_host_detection.hosts["www.test.com"]["timeout_requests"], 0)
        self.assertFalse(self.dead_host_detection.hosts["www.test.com"]["possibly_dead"])
        self.assertEqual(self.dead_host_detection.hosts["10.11.12.13:8080"]["request_count"], 0)
        self.assertEqual(self.dead_host_detection.hosts["10.11.12.13:8080"]["timeout_requests"], 0)
        self.assertFalse(self.dead_host_detection.hosts["10.11.12.13:8080"]["possibly_dead"])

    @async_test()
    async def test_on_timeout_increment_timeout_requests_for_host(self):
        for i in range(10):
            await self.dead_host_detection.before_attempt(Entry.create("http://example.com/"))
            await self.dead_host_detection.before_attempt(Entry.create("http://www.test.com/"))
            await self.dead_host_detection.before_attempt(Entry.create("http://10.10.10.10:8080/"))

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
    async def test_on_timeout_set_possibly_dead_to_true(self):
        self.dead_host_detection.hosts["example.com"] = \
            {"request_count": 0, "possibly_dead": True, "timeout_requests": 0}

        await self.dead_host_detection.on_timeout(Entry.create("http://example.com/"))

        self.assertTrue(self.dead_host_detection.hosts["example.com"]["possibly_dead"])

    @async_test()
    async def test_on_timeout_raise_offline_host_exception_if_timeout_requests_exceed_threshold(self):
        self.dead_host_detection.threshold = 20
        entries = [Entry.create("http://example.com/%d" % i) for i in range(30)]
        for entry in entries:
            await self.dead_host_detection.before_attempt(entry)

        for entry in entries[:19]:  # only 19 requests have timed out, no exception should be raised.
            await self.dead_host_detection.on_timeout(entry)

        with self.assertRaises(OfflineHostException):
            await self.dead_host_detection.on_timeout(entries[19])

    @async_test()
    async def test_on_timeout_raise_offline_host_exception_if_all_requests_timed_out(self):
        entries = [Entry.create("http://example.com/%d" % i) for i in range(10)]
        for entry in entries:
            await self.dead_host_detection.before_attempt(entry)

        for entry in entries[:-1]:  # last entry has not timed out, no exception should be raised.
            await self.dead_host_detection.on_timeout(entry)

        with self.assertRaises(OfflineHostException):
            await self.dead_host_detection.on_timeout(entries[-1])

    @async_test()
    async def test_on_timeout_add_dead_host_to_dead_host_list(self):
        entry = Entry.create("http://example.com/")
        self.dead_host_detection._is_host_dead = MagicMock(return_value=True)

        await self.dead_host_detection.before_attempt(entry)
        try:
            await self.dead_host_detection.on_timeout(entry)
        except OfflineHostException:
            pass

        self.assertIn("example.com", self.kb.dead_hosts)

    @async_test()
    async def test_before_request_raise_offline_host_exception_if_host_is_offline(self):
        entry = Entry.create("http://example.com/")
        await self.dead_host_detection.before_attempt(entry)
        self.dead_host_detection.dead_hosts = ["example.com"]

        with self.assertRaises(OfflineHostException):
            await self.dead_host_detection.before_request(entry)

    @async_test()
    async def test_on_error_set_possibly_dead_to_false(self):
        entry = Entry.create("http://example.com/")
        await self.dead_host_detection.before_attempt(entry)

        await self.dead_host_detection.on_error(entry)

        self.assertFalse(self.dead_host_detection.hosts["example.com"]["possibly_dead"])


class FutureAwaited(Exception):
    pass
