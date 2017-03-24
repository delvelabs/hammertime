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

from . import Engine
from ..ruleset import StopRequest


class RetryEngine(Engine):

    def __init__(self, engine, *, loop, stats, retry_count=0):
        self.request_engine = engine
        self.retry_count = retry_count
        self.stats = stats
        self.limiter = asyncio.Semaphore(50, loop=loop)

    async def perform(self, entry, heuristics):
        async with self.limiter:
            while True:
                try:
                    entry = await self.request_engine.perform(entry, heuristics=heuristics)
                    return entry
                except StopRequest:
                    if entry.result.attempt > self.retry_count:
                        raise
                    else:
                        entry.result.attempt += 1
                        self.stats.retries += 1
                        entry = entry._replace(response=None)

    async def close(self):
        if self.request_engine is not None:
            self.request_engine.close()
