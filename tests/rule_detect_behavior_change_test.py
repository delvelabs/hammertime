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
from hammertime.rules import DetectBehaviorChange
from hammertime.kb import KnowledgeBase
from hammertime.rules.behavior import BehaviorChanged
from hammertime.rules.simhash import Simhash


class TestDetectBehaviorChange(TestCase):

    @async_test()
    async def test_after_response_store_simhash_of_response_content_in_knowledge_base(self):
        entry = Entry.create("http://example.com/", response=StaticResponse(200, {}, content="data"))
        behavior_detection = DetectBehaviorChange()
        kb = KnowledgeBase()
        behavior_detection.set_kb(kb)

        await behavior_detection.after_response(entry)

        self.assertEqual(kb.behavior_buffer, [Simhash(entry.response.content).value])

    @async_test()
    async def test_after_response_pop_first_result_when_buffer_is_full(self):
        entry = Entry.create("http://example.com/", response=StaticResponse(200, {}, content="data"))
        behavior_detection = DetectBehaviorChange(buffer_size=5)
        behavior_detection.response_simhash_buffer = ["1", "2", "3", "4", "5"]

        await behavior_detection.after_response(entry)

        self.assertEqual(behavior_detection.response_simhash_buffer, ["2", "3", "4", "5", Simhash("data").value])

    @async_test()
    async def test_after_response_test_behavior_if_behavior_buffer_is_full(self):
        behavior_detection = DetectBehaviorChange(buffer_size=10)
        behavior_detection.response_simhash_buffer = ["data"] * 10
        behavior_detection._test_behavior = MagicMock(return_value=False)
        response = StaticResponse(200, {}, content="test")
        entry = Entry.create("http://example.com/", response=response)

        await behavior_detection.after_response(entry)

        behavior_detection._test_behavior.assert_called_once_with(entry)

    @async_test()
    async def test_after_response_dont_test_behavior_if_behavior_buffer_not_full(self):
        behavior_detection = DetectBehaviorChange(buffer_size=10)
        behavior_detection.response_simhash_buffer = ["data"] * 5
        behavior_detection._test_behavior = MagicMock(return_value=False)
        response = StaticResponse(200, {}, content="test")
        entry = Entry.create("http://example.com/", response=response)

        await behavior_detection.after_response(entry)

        behavior_detection._test_behavior.assert_not_called()

    @async_test()
    async def test_after_response_raise_exception_if_behavior_is_not_normal(self):
        behavior_detection = DetectBehaviorChange(buffer_size=10)
        behavior_detection.response_simhash_buffer = ["data"] * 10
        response = StaticResponse(200, {}, content="data")
        entry = Entry.create("http://example.com/", response=response)

        with self.assertRaises(BehaviorChanged):
            await behavior_detection.after_response(entry)
        self.assertTrue(behavior_detection.error_behavior)

    @async_test()
    async def test_after_response_dont_raise_exception_if_normal_behavior_restored(self):
        behavior_detection = DetectBehaviorChange(buffer_size=10)
        behavior_detection.response_simhash_buffer = ["data"] * 10
        behavior_detection.error_behavior = True
        response = StaticResponse(200, {}, content="test")
        entry = Entry.create("http://example.com/", response=response)

        await behavior_detection.after_response(entry)

        self.assertFalse(behavior_detection.error_behavior)

    @async_test()
    async def test_behavior_return_true_if_all_response_have_the_same_content(self):
        behavior_detection = DetectBehaviorChange(buffer_size=10)
        behavior_detection.response_simhash_buffer = [Simhash("data").value] * 10
        response = StaticResponse(200, {}, content="data")
        entry = Entry.create("http://example.com/", response=response)

        self.assertTrue(behavior_detection._test_behavior(entry))

    @async_test()
    async def test_behavior_return_false_if_not_all_response_have_the_same_content(self):
        behavior_detection = DetectBehaviorChange(buffer_size=10)
        behavior_detection.response_simhash_buffer = [Simhash("data").value] * 10
        response = StaticResponse(200, {}, content="test")
        entry = Entry.create("http://example.com/", response=response)

        self.assertFalse(behavior_detection._test_behavior(entry))
