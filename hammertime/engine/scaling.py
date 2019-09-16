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
from collections import namedtuple


Cohort = namedtuple('Cohort', ['scale', 'average_wait'])


class Policy:

    def get_semaphore(self):
        NotImplemented

    async def record(self, *, duration: float):
        NotImplemented


class StaticPolicy(Policy):
    """
    Default policy provider not using any special logic to improve. Simply use the specified
    concurrency.
    """

    def __init__(self, size):
        self.semaphore = asyncio.Semaphore(size)

    def get_semaphore(self):
        return self.semaphore

    async def record(self, *, duration: float):
        pass


class SlowStartPolicy(Policy):
    """
    Dynamic concurrency algorithm attempting to use remote resources as efficiently as possible
    for large volumes of requests. The policy will begin with a low concurrency and scale up as long
    as the remote host appears to handle the volume.

    - Record is called for each request with the amount of time spent waiting for the response.
    - Analysis is made at the end of each cohort.
    - Scales-up as long as the average response time is stable, indicating the remote server still has
      enough resources.
    - When performance degrades, mark the previous step as the ceiling and scale down below the ceiling
      to let the target recover. The target speed becomes locked.
    - Following the ceiling set, the target speed is used to adjust the concurrency. Scaling will never
      go over the ceiling. Attempt to scale up if duration is close to target, scale down otherwise.
    """

    def __init__(self, *, initial, minimum=1, maximum=100, cohort_size=200, tolerance=0.15):
        self.semaphore = ResizableSemaphore(initial=initial, minimum=minimum, maximum=maximum)
        self.cohort_size = cohort_size

        self._reset_cohort()
        self.cohorts = []
        self.has_mutation = True  # We begin on a new state, consider it changed
        self.increment = 2
        self.tolerance = tolerance
        self.ceiling_found = False
        self.target = None

    def get_semaphore(self):
        return self.semaphore

    @property
    def concurrency(self):
        return self.semaphore.current

    async def record(self, *, duration: float):
        self.cohort_duration += duration
        self.cohort_count += 1

        if self.cohort_count != self.cohort_size:
            return self.concurrency

        try:
            if self.has_mutation:
                # Skip cohort as it is tainted by an ongoing modification
                self.has_mutation = False
                return self.concurrency

            self.cohorts.append(Cohort(self.concurrency, self.cohort_duration / self.cohort_count))
        finally:
            self._reset_cohort()

        if len(self.cohorts) >= 2:
            self.has_mutation = await self._adjust_scale()

        return self.concurrency

    async def _adjust_scale(self):
        prev_scale, prev_time = self.cohorts[-2]
        current_scale, current_time = self.cohorts[-1]

        if not self.ceiling_found:
            # Before the ceiling is found, all cohorts are relatively stable Average the cohorts
            # to get a smooth target and avoid some unwanted fluctuations.
            #
            # Exclude the last cohort as it has not been analyzed yet and may well be the ceiling.
            self.target = sum(x for _, x in self.cohorts[0:-1]) / (len(self.cohorts) - 1)

        upper_bound = self.target * (1 + self.tolerance)

        if current_time > upper_bound and not self.semaphore.is_min:
            await self.semaphore.remove(self.increment)

            if not self.ceiling_found and prev_scale < current_scale:
                self.ceiling_found = True
                self.increment = 1

                await self.semaphore.remove(self.increment)
                self.semaphore.current_as_maximum()

        elif current_time < upper_bound and not self.semaphore.is_max:
            await self.semaphore.add(self.increment)

        # Return True if changed during the call (has mutation)
        return current_scale != self.semaphore.current

    def _reset_cohort(self):
        self.cohort_count = 0
        self.cohort_duration = 0.0


class ResizableSemaphore:

    """
    Semaphore-like locking mechanism allowing to change the amount of locks available.
    Scale-up is automatic while scaling down happens only when a lock is released if all
    locks are busy.
    """

    def __init__(self, *, minimum, maximum, initial):
        self.minimum = minimum
        self.maximum = maximum
        self.current = self._apply_bounds(initial)
        self.queue = asyncio.Queue()
        self.resize_lock = asyncio.Lock()
        self.extra = 0

        for _ in range(self.current):
            self.queue.put_nowait(0)

    @property
    def is_max(self):
        return self.current == self.maximum

    @property
    def is_min(self):
        return self.current == self.minimum

    def current_as_maximum(self):
        self.maximum = self.current

    async def add(self, quantity):
        async with self.resize_lock:
            target = self._apply_bounds(self.current + quantity)
            for _ in range(self.current, target):
                self.current += 1
                await self.queue.put(0)

    async def remove(self, quantity):
        async with self.resize_lock:
            target = self._apply_bounds(self.current - quantity)
            for _ in range(self.current, target, -1):
                try:
                    self.queue.get_nowait()
                except asyncio.QueueEmpty:
                    self.extra += 1

                self.current -= 1

    def _apply_bounds(self, value):
        return min(self.maximum, max(self.minimum, value))

    async def acquire(self):
        await self.queue.get()

    async def release(self):
        if self.extra > 0:
            async with self.resize_lock:
                if self.extra > 0:
                    # We need to reduce the concurrency, do not put this token back in circulation
                    self.extra -= 1
                    return

        await self.queue.put(0)

    async def __aenter__(self):
        await self.acquire()

    async def __aexit__(self, exc_type, exc, tb):
        await self.release()
