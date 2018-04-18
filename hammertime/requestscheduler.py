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


from asyncio.queues import Queue
from collections import deque


class RequestScheduler:

    def __init__(self, requests, *, loop, limit=1000):
        self.done = Queue(loop=loop)
        self.loop = loop
        self.wait_queue = deque(requests)
        self.pending_requests = []
        self.max_simultaneous_requests = limit
        self.schedule_max_possible_requests()

    def schedule_max_possible_requests(self):
        while len(self.pending_requests) < self.max_simultaneous_requests:
            try:
                self.schedule_request(self.wait_queue.popleft())
            except IndexError:
                return

    def schedule_request(self, request):
        task = self.loop.create_task(request)
        task.add_done_callback(self.on_completion)
        self.pending_requests.append(task)

    def on_completion(self, task):
        self.pending_requests.remove(task)
        self.done.put_nowait(task)
        try:
            self.schedule_request(self.wait_queue.popleft())
        except IndexError:
            pass

    async def __aiter__(self):
        return self

    async def __anext__(self):
        while not self.done.empty() or len(self.pending_requests) > 0 or len(self.wait_queue) > 0:
            return await self.done.get()
        raise StopAsyncIteration()
