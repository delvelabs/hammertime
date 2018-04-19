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
from .requestscheduler import RequestScheduler
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

        self.tasks = deque()
        self.closed = asyncio.Future(loop=loop)
        self.loop.add_signal_handler(signal.SIGINT, self._interrupt)
        self._success_iterator = None
        self._interrupted = False
        self._request_scheduler = RequestScheduler(loop=loop)

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
            # Return an exception as if it were a task when attempting to request on a closed engine
            future = asyncio.Future(loop=self.loop)
            future.set_exception(asyncio.CancelledError())
            return future

        self.stats.requested += 1
        future = self._request_scheduler.request(self._request(*args, **kwargs))
        self.tasks.append(future)
        future.add_done_callback(self._on_completion)
        return future

    async def _request(self, *args, **kwargs):
        try:
            entry = Entry.create(*args, **kwargs)
            entry = await self.request_engine.perform(entry, heuristics=self.heuristics)
            return entry
        except (HammerTimeException, asyncio.CancelledError):
            raise
        except Exception as e:
            logger.exception(e)
        finally:
            self.stats.completed += 1

    def collect_successful_requests(self):
        assert self._success_iterator is None, "collect_successful_requests() can only be called once."
        self._success_iterator = QueueIterator(loop=self.loop, has_pending_cb=lambda: len(self.tasks) > 0)

    def successful_requests(self):
        assert self._success_iterator is not None, \
               "You must call collect_successful_requests() prior to performing requests."
        return self._success_iterator

    def _on_completion(self, future):
        self._drain(future)
        self.tasks.remove(future)

        if self._success_iterator:
            # Checking exception conditions explicitly to avoid using try/except blocks
            entry = future.result() if not future.cancelled() and not future.exception() else None

            self._success_iterator.complete(entry)

    def _drain(self, future):
        try:
            future.result()
        except (HammerTimeException, asyncio.CancelledError):
            pass
        except Exception as e:
            logger.exception(e)

    async def _cancel_tasks(self):
        for future in self.tasks:
            if not future.done():
                future.cancel()
        if len(self.tasks):
            await asyncio.wait(self.tasks, loop=self.loop, return_when=asyncio.ALL_COMPLETED)

    async def close(self):
        if not self.is_closed:
            await self._cancel_tasks()
            for future in self.tasks:
                if future.done():
                    self._drain(future)

            if self.request_engine is not None:
                await self.request_engine.close()
            self.closed.set_result(None)

    def set_proxy(self, proxy):
        self.request_engine.set_proxy(proxy)

    def _interrupt(self):
        if not self._interrupted:
            self._interrupted = True
            asyncio.ensure_future(self.close(), loop=self.loop)


class QueueIterator:

    def __init__(self, *, loop, has_pending_cb):
        self.queue = asyncio.Queue(loop=loop)
        self.has_pending = has_pending_cb

    def complete(self, entry):
        if entry or not self.has_pending():
            self.queue.put_nowait(entry)

    async def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            out = None
            if not self.queue.empty():
                out = self.queue.get_nowait()
            elif self.has_pending():
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
