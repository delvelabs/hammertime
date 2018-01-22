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

from fixtures import async_test, fake_future
from hammertime.rules import DeadHostDetection
from hammertime.kb import KnowledgeBase
from hammertime.http import Entry
from hammertime.rules.deadhostdetection import OfflineHostException


class TestDeadHostDetection(TestCase):

    def setUp(self):
        pass

    @async_test()
    async def test_before_attempt_increment_request_count_for_host(self):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        netloc0 = "example.com"
        netloc1 = "www.test.example"
        netloc2 = "10.0.0.10:8080"

        await detection.before_attempt(Entry.create("http://example.com/test"))
        await detection.before_attempt(Entry.create("http://example.com/12"))

        await detection.before_attempt(Entry.create("http://www.test.example/index.html"))

        await detection.before_attempt(Entry.create("http://10.0.0.10:8080/qw"))
        await detection.before_attempt(Entry.create("http://10.0.0.10:8080/we"))
        await detection.before_attempt(Entry.create("http://10.0.0.10:8080/rt"))

        self.assertEqual(kb.hosts[netloc0]["request_count"], 2)
        self.assertEqual(kb.hosts[netloc1]["request_count"], 1)
        self.assertEqual(kb.hosts[netloc2]["request_count"], 3)

    @async_test()
    async def test_before_attempt_set_lock_on_new_host_with_pending_requests(self):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        entry = Entry.create("http://example.com/")

        await detection.before_attempt(entry)

        self.assertIsInstance(kb.hosts["example.com"]["pending_requests"], asyncio.Future)

    @async_test()
    async def test_before_attempt_does_nothing_if_previous_request_successful(self):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        future = MagicMock()
        future.done.return_value = True
        kb.hosts["example.com"] = {"pending_requests": future, "request_count": 0}

        await detection.before_attempt(Entry.create("http://example.com/"))

        self.assertEqual(kb.hosts["example.com"]["request_count"], 0)

    @async_test()
    async def test_before_attempt_await_pending_requests_for_host_before_retries(self, loop):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        entry = Entry.create("http://example.com/")
        entry.result.attempt = 2
        future = asyncio.Future(loop=loop)
        future.done = MagicMock(return_value=False)
        future.set_exception(FutureAwaited())
        kb.hosts["example.com"] = {"request_count": 1, "pending_requests": future}

        with self.assertRaises(FutureAwaited):
            await detection.before_attempt(entry)

    @async_test()
    async def test_before_attempt_raise_offline_host_exception_for_retries_if_all_first_attempts_failed(self, loop):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        entry = Entry.create("http://example.com/")
        entry.result.attempt = 2
        future = asyncio.Future(loop=loop)
        future.done = MagicMock(return_value=False)
        future.set_exception(OfflineHostException())
        kb.hosts["example.com"] = {"request_count": 1, "pending_requests": future}

        with self.assertRaises(OfflineHostException):
            await detection.before_attempt(entry)

    @async_test()
    async def test_after_headers_set_lock_to_done_for_host_and_reset_state(self, loop):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        kb.hosts["example.com"] = {"request_count": 2, "pending_requests": asyncio.Future(loop=loop), "timeout_requests": 1}
        kb.hosts["www.test.com"] = {"request_count": 1, "pending_requests": asyncio.Future(loop=loop), "timeout_requests": 1}
        kb.hosts["10.11.12.13:8080"] = {"request_count": 3, "pending_requests": asyncio.Future(loop=loop), "timeout_requests": 2}

        await detection.after_headers(Entry.create("http://example.com/"))
        await detection.after_headers(Entry.create("http://www.test.com/"))
        await detection.after_headers(Entry.create("http://10.11.12.13:8080/"))

        self.assertEqual(kb.hosts["example.com"]["request_count"], 0)
        self.assertEqual(kb.hosts["example.com"]["timeout_requests"], 0)
        self.assertTrue(kb.hosts["example.com"]["pending_requests"].done())
        self.assertEqual(kb.hosts["www.test.com"]["request_count"], 0)
        self.assertEqual(kb.hosts["www.test.com"]["timeout_requests"], 0)
        self.assertTrue(kb.hosts["www.test.com"]["pending_requests"].done())
        self.assertEqual(kb.hosts["10.11.12.13:8080"]["request_count"], 0)
        self.assertEqual(kb.hosts["10.11.12.13:8080"]["timeout_requests"], 0)
        self.assertTrue(kb.hosts["10.11.12.13:8080"]["pending_requests"].done())

    @async_test()
    async def test_on_timeout_increment_timeout_requests_for_host(self):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        for i in range(10):
            await detection.before_attempt(Entry.create("http://example.com/"))
            await detection.before_attempt(Entry.create("http://www.test.com/"))
            await detection.before_attempt(Entry.create("http://10.10.10.10:8080/"))

        await detection.on_timeout(Entry.create("http://example.com/"))
        await detection.on_timeout(Entry.create("http://example.com/"))

        await detection.on_timeout(Entry.create("http://www.test.com/"))

        await detection.on_timeout(Entry.create("http://10.10.10.10:8080/"))
        await detection.on_timeout(Entry.create("http://10.10.10.10:8080/"))
        await detection.on_timeout(Entry.create("http://10.10.10.10:8080/"))

        self.assertEqual(kb.hosts["example.com"]["timeout_requests"], 2)
        self.assertEqual(kb.hosts["www.test.com"]["timeout_requests"], 1)
        self.assertEqual(kb.hosts["10.10.10.10:8080"]["timeout_requests"], 3)

    @async_test()
    async def test_on_timeout_set_new_lock_for_host_previously_up(self, loop):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        future = fake_future(None, loop=loop)
        kb.hosts["example.com"] = {"request_count": 0, "pending_requests": future, "timeout_requests": 0}

        await detection.on_timeout(Entry.create("http://example.com/"))

        self.assertFalse(kb.hosts["example.com"]["pending_requests"].done())

    @async_test()
    async def test_on_timeout_raise_offline_host_exception_if_timeout_requests_exceed_threshold(self):
        detection = DeadHostDetection(threshold=20)
        kb = KnowledgeBase()
        detection.set_kb(kb)
        entries = [Entry.create("http://example.com/%d" % i) for i in range(30)]
        for entry in entries:
            await detection.before_attempt(entry)

        for entry in entries[:19]:  # only 19 requests have timed out, no exception should be raised.
            await detection.on_timeout(entry)

        with self.assertRaises(OfflineHostException):
            await detection.on_timeout(entries[19])

    @async_test()
    async def test_on_timeout_raise_offline_host_exception_if_all_requests_timed_out(self):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        entries = [Entry.create("http://example.com/%d" % i) for i in range(10)]
        for entry in entries:
            await detection.before_attempt(entry)

        for entry in entries[:-1]:  # last entry has not timed out, no exception should be raised.
            await detection.on_timeout(entry)

        with self.assertRaises(OfflineHostException):
            await detection.on_timeout(entries[-1])

    @async_test()
    async def test_on_timeout_set_offline_host_exception_for_lock_if_all_requests_timed_out(self):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        entry = Entry.create("http://example.com/")

        await detection.before_attempt(entry)
        try:
            await detection.on_timeout(entry)
        except OfflineHostException:
            pass

        with self.assertRaises(OfflineHostException):
            await kb.hosts["example.com"]["pending_requests"]

    @async_test()
    async def test_on_timeout_dont_set_new_exception_for_lock_if_previous_request_timed_out(self):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        entry = Entry.create("http://example.com/")
        await detection.before_attempt(entry)
        expected = OfflineHostException("exception 1")
        kb.hosts["example.com"]["pending_requests"].set_exception(expected)

        try:
            await detection.on_timeout(entry)
        except OfflineHostException:
            pass

        self.assertEqual(expected, kb.hosts["example.com"]["pending_requests"].exception())

    @async_test()
    async def test_before_request_raise_offline_host_exception_if_host_is_offline(self):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        entry = Entry.create("http://example.com/")
        await detection.before_attempt(entry)
        kb.hosts["example.com"]["pending_requests"].set_exception(OfflineHostException())

        with self.assertRaises(OfflineHostException):
            await detection.before_request(entry)

    @async_test()
    async def test_on_error_set_pending_lock_to_done(self):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        entry = Entry.create("http://example.com/")
        await detection.before_attempt(entry)

        await detection.on_error(entry)

        self.assertTrue(kb.hosts["example.com"]["pending_requests"].done())


class FutureAwaited(Exception):
    pass
