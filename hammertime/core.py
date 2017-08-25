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

import time
import asyncio
import logging
from collections import deque

from .http import Entry
from .ruleset import Heuristics, HammerTimeException
from .engine import RetryEngine
import signal


logger = logging.getLogger(__name__)


class HammerTime:

    def __init__(self, loop=None, request_engine=None, kb=None, retry_count=0, proxy=None):
        self.loop = loop
        self.stats = Stats()

        self.request_engine = RetryEngine(request_engine, loop=loop, stats=self.stats, retry_count=retry_count)
        if proxy is not None:
            self.request_engine.set_proxy(proxy)
        self.heuristics = Heuristics(kb=kb, request_engine=self.request_engine)

        self.completed_queue = asyncio.Queue(loop=self.loop)
        self.tasks = deque()
        self.closed = asyncio.Future(loop=loop)
        self.loop.add_signal_handler(signal.SIGINT, self._interrupt)

    @property
    def completed_count(self):
        return self.stats.completed

    @property
    def requested_count(self):
        return self.stats.requested

    @property
    def is_closed(self):
        return self.closed.done()

    def request(self, *args, **kwargs):
        if self.is_closed:
            raise asyncio.CancelledError()
        self.stats.requested += 1
        task = self.loop.create_task(self._request(*args, **kwargs))
        self.tasks.append(task)
        return task

    async def _request(self, *args, **kwargs):
        try:
            entry = Entry.create(*args, **kwargs)
            entry = await self.request_engine.perform(entry, heuristics=self.heuristics)
            await self.completed_queue.put(entry)
            return entry
        except (HammerTimeException, asyncio.CancelledError):
            raise
        except Exception as e:
            logger.exception(e)
        finally:
            self.stats.completed += 1
            self.loop.call_soon(self._check_completion)

    def successful_requests(self):
        self._check_completion()
        return QueueIterator(self.completed_queue)

    def _check_completion(self):
        try:
            while True:
                task = self.tasks.popleft()
                if task.done():
                    self._drain(task)
                else:
                    self.tasks.appendleft(task)
                    return
        except IndexError:
            self.completed_queue.put_nowait(None)

    def _drain(self, task):
        try:
            task.result()
        except (HammerTimeException, asyncio.CancelledError):
            pass
        except Exception as e:
            logger.exception(e)

    async def close(self):
        if not self.is_closed:
            for t in self.tasks:
                if t.done():
                    self._drain(t)
                else:
                    t.cancel()

            if self.request_engine is not None:
                await self.request_engine.close()
            self.closed.set_result(None)

    def set_proxy(self, proxy):
        self.request_engine.set_proxy(proxy)

    def _interrupt(self):
        asyncio.ensure_future(self.close(), loop=self.loop)


class QueueIterator:

    def __init__(self, queue):
        self.queue = queue

    async def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            out = None
            if not self.queue.empty():
                out = self.queue.get_nowait()
            else:
                out = await self.queue.get()

            if out is None:
                raise StopAsyncIteration

            return out
        except asyncio.queues.QueueEmpty:
            raise StopAsyncIteration


class Stats:

    def __init__(self):
        self.init = time.time()
        self.requested = 0
        self.completed = 0
        self.retries = 0

    @property
    def duration(self):
        return time.time() - self.init

    @property
    def rate(self):
        return self.completed / self.duration
