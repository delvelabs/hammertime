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
from weakref import ref as weakref

from . import Engine
from ..ruleset import StopRequest


class RetryEngine(Engine):

    def __init__(self, engine, *, loop, stats, retry_count=0, retry_delay=1.0):
        self.request_engine = engine
        self.retry_count = retry_count
        self.stats = stats
        self.general_limiter = asyncio.Semaphore(50, loop=loop)
        self.priority_limiter = asyncio.Semaphore(10, loop=loop)
        self.default_heuristics = None
        self.retry_delay = retry_delay

    async def perform(self, entry, heuristics):
        if self.default_heuristics is None:
            self.default_heuristics = weakref(heuristics)

        return await self._perform(self.general_limiter, entry, heuristics)

    async def perform_high_priority(self, entry, heuristics=None):
        return await self._perform(self.priority_limiter, entry, heuristics or self.default_heuristics())

    async def _perform(self, limiter, entry, heuristics):
        while True:
            try:
                async with limiter:
                    entry = await self.request_engine.perform(entry, heuristics=heuristics)
                await heuristics.on_request_successful(entry)
                return entry
            except StopRequest:
                if entry.result.attempt > self.retry_count:
                    raise
                else:
                    entry.result.attempt += 1
                    self.stats.retries += 1
                    entry.response = None
                    await asyncio.sleep(self.retry_delay)

    async def close(self):
        if self.request_engine is not None:
            await self.request_engine.close()

    def set_proxy(self, proxy):
        if self.request_engine is not None:
            self.request_engine.set_proxy(proxy)
