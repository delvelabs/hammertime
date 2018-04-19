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


import asyncio
from unittest import TestCase
from unittest.mock import MagicMock, call

from fixtures import async_test
from hammertime.requestscheduler import RequestScheduler


class TestRequestScheduler(TestCase):

    def test_schedule_maximum_number_of_requests_on_creation(self):
        loop = MagicMock()
        requests = [i for i in range(100)]
        limit = 10
        loop.create_task = MagicMock(return_value=MagicMock())

        scheduler = RequestScheduler(loop=loop, limit=limit)
        for request in requests:
            scheduler.request(request)

        expected = [call(i) for i in range(limit)]
        loop.create_task.assert_has_calls(expected)
        self.assertEqual(scheduler.pending_requests, [loop.create_task.return_value]*limit)

    def test_remove_scheduled_futures_from_wait_list(self):
        loop = MagicMock()
        request_count = 100
        requests = [i for i in range(request_count)]
        limit = 10

        scheduler = RequestScheduler(loop=loop, limit=limit)
        for request in requests:
            scheduler.request(request)

        self.assertEqual(len(scheduler.wait_queue), request_count - limit)

    @async_test()
    async def test_remove_completed_task_from_pending_requests_list(self, loop):
        async def dummy_coro():
            await asyncio.sleep(0)
        request = dummy_coro()
        scheduler = RequestScheduler(loop=loop)
        future = scheduler.request(request)
        await future
        self.assertEqual(len(scheduler.pending_requests), 0)

    @async_test()
    async def test_schedule_waiting_task_when_task_is_done(self, loop):
        async def dummy_coro(result):
            await asyncio.wait_for(result, timeout=5)
            return result

        result0 = asyncio.Future(loop=loop)
        result1 = asyncio.Future(loop=loop)
        scheduler = RequestScheduler(loop=loop, limit=1)
        future0 = scheduler.request(dummy_coro(result0))
        future1 = scheduler.request(dummy_coro(result1))
        result0.set_result(None)

        self.assertEqual(await future0, result0)
        self.assertEqual(len(scheduler.wait_queue), 0)
        self.assertEqual(len(scheduler.pending_requests), 1)

        result1.set_result(None)
        self.assertEqual(await future1, result1)
        self.assertEqual(len(scheduler.pending_requests), 0)
