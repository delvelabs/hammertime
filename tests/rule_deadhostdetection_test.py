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

from fixtures import async_test, fake_future
from hammertime.rules import DeadHostDetection
from hammertime.kb import KnowledgeBase
from hammertime.http import Entry
from hammertime.rules.deadhostdetection import OfflineHostException


class TestDeadHostDetection(TestCase):

    def setUp(self):
        pass

    @async_test()
    async def test_before_request_register_request(self):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        entry = Entry.create("http://example.com/")

        await detection.before_request(entry)

        self.assertIn("http://example.com/", kb.pending_requests)

    @async_test()
    async def test_after_headers_remove_pending_request(self):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        kb.pending_requests.append("http://example.com/")
        entry = Entry.create("http://example.com/")

        await detection.after_headers(entry)

        self.assertNotIn("http://example.com/", kb.pending_requests)

    @async_test()
    async def test_on_timeout_register_failed_request(self):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        entry = Entry.create("http://example.com/")

        await detection.on_timeout(entry)

        self.assertIn("http://example.com/", kb.timeout_requests)

    @async_test()
    async def test_on_timeout_raise_offline_host_exception_if_all_requests_timed_out(self):
        detection = DeadHostDetection()
        kb = KnowledgeBase()
        detection.set_kb(kb)
        entries = [Entry.create("http://example.com/%d" % i) for i in range(10)]
        for entry in entries:
            await detection.before_request(entry)

        for entry in entries[:-1]:  # last entry has not timed out, no exception should be raised.
            await detection.on_timeout(entry)

        with self.assertRaises(OfflineHostException):
            await detection.on_timeout(entries[-1])
