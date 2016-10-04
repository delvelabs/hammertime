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
import logging
from .http import Entry
from .ruleset import Heuristics, StopRequest


logger = logging.getLogger(__name__)


class HammerTime:

    def __init__(self, loop=None, request_engine=None):
        self.loop = loop or asyncio.get_event_loop()
        self.request_engine = request_engine
        self.completed_count = 0
        self.requested_count = 0
        self.heuristics = Heuristics()
        self.completed = None
        self.completed_queue = asyncio.Queue(loop=self.loop)

    def request(self, *args, **kwargs):
        self.requested_count += 1
        return self.loop.create_task(self._request(*args, **kwargs))

    async def _request(self, *args, **kwargs):
        try:
            entry = Entry.create(*args, **kwargs)
            entry = await self.request_engine.perform(entry, heuristics=self.heuristics)
            await self.completed_queue.put(entry)
            return entry
        except StopRequest:
            raise
        except Exception as e:
            logger.exception(e)
        finally:
            self.completed_count += 1
            self._check_completion()

    def successful_requests(self):
        self._initialize_completion_check()
        return QueueIterator(self.completed_queue, self.completed)

    def _initialize_completion_check(self):
        if self.completed is None or self.completed.done():
            self.completed = asyncio.Future(loop=self.loop)
            self._check_completion()

    def _check_completion(self):
        if self.completed is not None and self.requested_count == self.completed_count:
            self.completed.set_result(True)

    async def close(self):
        pass


class QueueIterator:

    def __init__(self, queue, completed_future):
        self.queue = queue
        self.completed_future = completed_future

    async def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            out = None
            if self.completed_future.done() and not self.queue.empty():
                out = self.queue.get_nowait()
            elif not self.completed_future.done():
                out = await self.queue.get()

            if out is None:
                raise StopAsyncIteration

            return out
        except asyncio.queues.QueueEmpty:
            raise StopAsyncIteration
