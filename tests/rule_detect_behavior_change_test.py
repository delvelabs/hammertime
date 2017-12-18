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
from hammertime.http import Entry, StaticResponse
from hammertime.rules import DetectBehaviorChange, RejectBehaviorChange
from hammertime.kb import KnowledgeBase
from hammertime.rules.behavior import BehaviorChanged
from hammertime.rules.simhash import Simhash


class TestDetectBehaviorChange(TestCase):

    def setUp(self):
        self.entry = Entry.create("http://example.com/", response=StaticResponse(200, {}, content="data"))
        self.behavior_detection = DetectBehaviorChange()
        self.kb = KnowledgeBase()
        self.behavior_detection.set_kb(self.kb)

    @async_test()
    async def test_after_response_store_simhash_of_response_content_in_knowledge_base(self):
        await self.behavior_detection.after_response(self.entry)

        self.assertEqual(self.kb.behavior_buffer, [Simhash(self.entry.response.content).value])

    @async_test()
    async def test_after_response_pop_first_result_when_buffer_is_full(self):
        self.kb.behavior_buffer.extend([str(i) for i in range(10)])

        await self.behavior_detection.after_response(self.entry)

        self.assertEqual(self.kb.behavior_buffer, ["1", "2", "3", "4", "5", "6", "7", "8", "9", Simhash("data").value])

    @async_test()
    async def test_after_response_test_behavior_if_behavior_buffer_is_full(self):
        self.kb.behavior_buffer.extend(["data"] * 10)
        self.behavior_detection._is_error_behavior = MagicMock(return_value=False)

        await self.behavior_detection.after_response(self.entry)

        self.behavior_detection._is_error_behavior.assert_called_once_with(self.entry)

    @async_test()
    async def test_after_response_dont_test_behavior_if_behavior_buffer_not_full(self):
        self.kb.behavior_buffer.extend(["data"] * 5)
        self.behavior_detection._is_error_behavior = MagicMock(return_value=False)

        await self.behavior_detection.after_response(self.entry)

        self.behavior_detection._is_error_behavior.assert_not_called()

    @async_test()
    async def test_after_response_set_flag_in_entry_arguments_if_behavior_is_not_normal(self):
        self.kb.behavior_buffer.extend(["data"] * 10)

        await self.behavior_detection.after_response(self.entry)

        self.assertTrue(self.entry.arguments["error_behavior"])
        self.assertTrue(self.behavior_detection.error_behavior)

    @async_test()
    async def test_after_response_dont_set_flag_in_entry_arguments_if_normal_behavior_restored(self):
        self.kb.behavior_buffer.extend(["test"] * 10)
        self.behavior_detection.error_behavior = True

        await self.behavior_detection.after_response(self.entry)

        self.assertFalse(self.entry.arguments["error_behavior"])
        self.assertFalse(self.behavior_detection.error_behavior)

    @async_test()
    async def test_is_error_behavior_return_true_if_all_response_have_the_same_content(self):
        self.behavior_detection.response_simhash_buffer = [Simhash("data").value] * 10

        error_behavior = self.behavior_detection._is_error_behavior(self.entry)

        self.assertTrue(error_behavior)

    @async_test()
    async def test_is_error_behavior_return_false_if_not_all_response_have_the_same_content(self):
        self.behavior_detection.response_simhash_buffer = [Simhash("data").value] * 10
        response = StaticResponse(200, {}, content="test")
        entry = Entry.create("http://example.com/", response=response)

        error_behavior = self.behavior_detection._is_error_behavior(entry)

        self.assertFalse(error_behavior)


class TestRejectBehaviorChange(TestCase):

    def setUp(self):
        self.heuristic = RejectBehaviorChange()
        self.heuristic.behavior_change_detection = MagicMock()
        response = StaticResponse(200, {}, content="test")
        self.entry = Entry.create("http://example.com/", response=response)

    @async_test()
    async def test_after_response_check_for_behavior_change(self, loop):
        self.heuristic.behavior_change_detection.after_response.return_value = fake_future(None, loop)

        await self.heuristic.after_response(self.entry)

        self.heuristic.behavior_change_detection.after_response.assert_called_once_with(self.entry)

    @async_test()
    async def test_after_response_raise_exception_if_behavior_changed(self, loop):
        self.heuristic.behavior_change_detection.after_response.return_value = fake_future(None, loop)
        response = StaticResponse(200, {}, content="test")
        entry = Entry.create("http://example.com/", response=response, arguments={"error_behavior": True})

        with self.assertRaises(BehaviorChanged):
            await self.heuristic.after_response(entry)
