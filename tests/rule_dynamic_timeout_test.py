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
from unittest.mock import patch, MagicMock
from fixtures import async_test

from hammertime.rules import DynamicTimeout
from hammertime.http import Entry
from hammertime.kb import KnowledgeBase
from statistics import stdev, mean


class DynamicTimeoutTest(TestCase):

    def setUp(self):
        self.retries = 3
        self.max_timeout = 10
        self.min_timeout = 0.2
        self.sample_size = 100
        self.rule = DynamicTimeout(min_timeout=self.min_timeout, max_timeout=self.max_timeout, retries=self.retries,
                                   sample_size=self.sample_size)
        self.knowledge_base = KnowledgeBase()
        self.rule.set_kb(self.knowledge_base)
        self.entry_factory = lambda: Entry.create("http://example.com")

    @async_test()
    async def test_before_request_set_timeout_to_80_percent_of_max_if_not_enough_samples(self):
        entry = self.entry_factory()

        await self.rule.before_request(entry)

        self.assertEqual(entry.arguments["timeout"], self.max_timeout * 0.8)

    @async_test()
    async def test_before_request_reduce_timeout_if_enough_successful_request(self):
        delays = [0.5] * self.sample_size
        self.knowledge_base.timeout_manager.request_delays = delays
        entry = self.entry_factory()

        await self.rule.before_request(entry)

        self.assertEqual(entry.arguments["timeout"], mean(delays) * 2 + stdev(delays) * 5)

    @async_test()
    async def test_before_request_augment_timeout_if_request_failed(self):
        entry = self.entry_factory()
        timeout = 1
        entry.arguments["timeout"] = timeout
        await self.rule.on_timeout(entry)

        await self.rule.before_request(entry)

        self.assertEqual(entry.arguments["timeout"], timeout * 2)

    @async_test()
    async def test_timeout_dont_exceed_max(self):
        entry = self.entry_factory()
        timeout = self.max_timeout
        entry.arguments["timeout"] = timeout
        await self.rule.on_timeout(entry)

        await self.rule.before_request(entry)

        self.assertEqual(entry.arguments["timeout"], self.max_timeout)

    @async_test()
    async def test_timeout_always_greater_than_min_timeout(self):
        self.knowledge_base.timeout_manager.request_delays = [0.01] * self.sample_size
        entry = self.entry_factory()

        await self.rule.before_request(entry)

        self.assertEqual(entry.arguments["timeout"], self.min_timeout)

    @async_test()
    async def test_on_timeout_add_failed_request_to_knowledge_base(self):
        entry = self.entry_factory()
        entry.arguments["timeout"] = 1

        await self.rule.on_timeout(entry)

        self.assertEqual(self.knowledge_base.timeout_manager.requests_successful, [False])

    @async_test()
    async def test_before_request_set_start_time_of_request(self):
        entry = self.entry_factory()

        with patch("hammertime.rules.timeout.time", MagicMock(return_value=100)):
            await self.rule.before_request(entry)

            self.assertEqual(entry.arguments["start_time"], 100)

    @async_test()
    async def test_before_request_use_max_timeout_if_last_attempt(self):
        entry = self.entry_factory()
        entry.result.attempt = self.retries + 1
        entry.arguments["timeout"] = 1

        await self.rule.before_request(entry)

        self.assertEqual(entry.arguments["timeout"], self.max_timeout)

    @async_test()
    async def test_after_headers_add_request_time_to_knowledge_base(self):
        entry = self.entry_factory()
        entry.arguments["start_time"] = 10

        with patch("hammertime.rules.timeout.time", MagicMock(return_value=20)):
            await self.rule.after_headers(entry)

            self.assertEqual(self.knowledge_base.timeout_manager.request_delays[0], 10)

    @async_test()
    async def test_after_headers_add_successful_request_to_knowledge_base(self):
        entry = self.entry_factory()
        entry.arguments["start_time"] = 10

        await self.rule.after_headers(entry)

        self.assertEqual(self.knowledge_base.timeout_manager.requests_successful, [True])

    @async_test()
    async def test_erase_last_failure_if_no_failure_after_long_time(self):
        delays = [self.min_timeout] * (self.sample_size * 5 + 1)
        self.knowledge_base.timeout_manager.request_delays = delays
        self.knowledge_base.timeout_manager.requests_successful = [True] * (self.sample_size * 5 + 1)
        self.knowledge_base.timeout_manager.last_retry_timeout = self.max_timeout
        entry = self.entry_factory()

        await self.rule.before_request(entry)

        self.assertIsNone(self.knowledge_base.timeout_manager.last_retry_timeout)

    @async_test()
    async def test_erase_old_data(self):
        delays = [self.min_timeout] * self.sample_size * 5
        self.knowledge_base.timeout_manager.request_delays = delays
        self.knowledge_base.timeout_manager.requests_successful = [True] * self.sample_size * 5
        entry = self.entry_factory()

        await self.rule.before_request(entry)
        await self.rule.after_headers(entry)
        await self.rule.before_request(entry)

        self.assertEqual(len(self.knowledge_base.timeout_manager.request_delays), self.sample_size)
        self.assertEqual(len(self.knowledge_base.timeout_manager.requests_successful), self.sample_size)
