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

from fixtures import async_test
from hammertime.http import Entry, StaticResponse
from hammertime.rules import DetectBehaviorChange, RejectErrorBehavior
from hammertime.kb import KnowledgeBase
from hammertime.rules.behavior import BehaviorError
from hammertime.rules.simhash import Simhash


class TestDetectBehaviorChange(TestCase):

    def setUp(self):
        self.entry = Entry.create("http://example.com/", response=StaticResponse(200, {}, content="data"))
        self.behavior_detection = DetectBehaviorChange()
        self.kb = KnowledgeBase()
        self.behavior_detection.set_kb(self.kb)

    @async_test()
    async def test_on_request_successful_store_simhash_of_response_content_in_knowledge_base(self):
        await self.behavior_detection.on_request_successful(self.entry)

        self.assertEqual(self.behavior_detection.behavior_buffer, [Simhash(self.entry.response.content).value])

    @async_test()
    async def test_on_request_successful_pop_first_result_when_buffer_is_full(self):
        self.behavior_detection.behavior_buffer.extend([i for i in range(10)])

        await self.behavior_detection.on_request_successful(self.entry)

        self.assertEqual(self.behavior_detection.behavior_buffer, [1, 2, 3, 4, 5, 6, 7, 8, 9, Simhash("data").value])

    @async_test()
    async def test_on_request_successful_test_behavior_if_behavior_buffer_is_full(self):
        self.behavior_detection.behavior_buffer.extend(["data"] * 10)
        self.behavior_detection._is_error_behavior = MagicMock(return_value=False)
        simhash = Simhash("value")
        self.behavior_detection._hash = MagicMock(return_value=simhash)

        await self.behavior_detection.on_request_successful(self.entry)

        self.behavior_detection._is_error_behavior.assert_called_once_with(simhash)

    @async_test()
    async def test_on_request_successful_dont_test_behavior_if_behavior_buffer_not_full(self):
        self.behavior_detection.behavior_buffer.extend(["data"] * 5)
        self.behavior_detection._is_error_behavior = MagicMock(return_value=False)

        await self.behavior_detection.on_request_successful(self.entry)

        self.behavior_detection._is_error_behavior.assert_not_called()

    @async_test()
    async def test_on_request_successful_permanently_flag_bad_behavior_even_if_normal_status_occurs(self):
        self.behavior_detection.behavior_buffer.extend(["data"] * 10)

        await self.behavior_detection.on_request_successful(self.entry)
        self.assertTrue(self.entry.result.error_behavior, "State should have been recorded")

        self.entry.response.content = "good response"
        await self.behavior_detection.on_request_successful(self.entry)

        self.behavior_detection._is_error_behavior = MagicMock(return_value=False)

        self.entry.response.content = "data"
        await self.behavior_detection.on_request_successful(self.entry)

        self.behavior_detection._is_error_behavior.assert_not_called()
        self.assertTrue(self.entry.result.error_behavior)

    @async_test()
    async def test_on_request_successful_set_flag_in_entry_result_if_behavior_is_not_normal(self):
        self.behavior_detection.behavior_buffer.extend(["data"] * 10)

        await self.behavior_detection.on_request_successful(self.entry)

        self.assertTrue(self.entry.result.error_behavior)
        self.assertTrue(self.behavior_detection.error_behavior)

    @async_test()
    async def test_safe_code_does_not_trigger_error(self):
        self.entry.response.code = 404
        self.behavior_detection.behavior_buffer.extend(["data"] * 10)

        await self.behavior_detection.on_request_successful(self.entry)

        self.assertFalse(self.entry.result.error_behavior)
        self.assertFalse(self.behavior_detection.error_behavior)

    @async_test()
    async def test_on_request_successful_dont_set_flag_in_entry_result_if_normal_behavior_restored(self):
        self.behavior_detection.behavior_buffer.extend(["test"] * 10)
        self.behavior_detection.error_behavior = True

        await self.behavior_detection.on_request_successful(self.entry)

        self.assertFalse(self.entry.result.error_behavior)
        self.assertFalse(self.behavior_detection.error_behavior)


class TestRejectErrorBehavior(TestCase):

    def setUp(self):
        self.heuristic = RejectErrorBehavior()
        self.entry = Entry.create("http://example.com/")

    @async_test()
    async def test_on_request_successful_dont_raise_if_no_behavior_error(self):
        self.entry.result.error_behavior = False

        try:
            await self.heuristic.on_request_successful(self.entry)
        except BehaviorError:
            self.fail("Request should not be rejected.")

    @async_test()
    async def test_on_request_successful_raise_exception_if_behavior_changed(self):
        self.entry.result.error_behavior = True

        with self.assertRaises(BehaviorError):
            await self.heuristic.on_request_successful(self.entry)
