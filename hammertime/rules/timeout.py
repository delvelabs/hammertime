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


from time import time
from statistics import mean, stdev


class DynamicTimeout:

    def __init__(self, min_timeout, max_timeout, sample_size=200):
        self.min_timeout = min_timeout
        self.max_timeout = max_timeout
        self.timeout_manager = TimeoutManager(min_timeout, max_timeout, sample_size)
        self.retry_count = 0

    def set_kb(self, kb):
        kb.timeout_manager = self.timeout_manager

    def load_kb(self, kb):
        self.timeout_manager = kb.timeout_manager

    def set_engine(self, engine):
        self.retry_count = engine.retry_count

    async def before_request(self, entry):
        if self._is_last_attempt(entry):
            entry.arguments["timeout"] = self.max_timeout
        else:
            entry.arguments["timeout"] = self.timeout_manager.get_timeout()
        entry.arguments["start_time"] = time()

    async def after_headers(self, entry):
        self.timeout_manager.add_successful_request(entry)

    async def on_timeout(self, entry):
        self.timeout_manager.add_failed_request(entry)

    def _is_last_attempt(self, entry):
        return entry.result.attempt > self.retry_count if self.retry_count != 0 else False


class TimeoutManager:

    def __init__(self, min_timeout, max_timeout, sample_size):
        self.min_timeout = min_timeout
        self.max_timeout = max_timeout
        self.request_delays = []
        self.samples_length = sample_size
        self.requests_successful = []
        self.last_retry_timeout = None

    def add_failed_request(self, entry):
        self.requests_successful.append(False)
        self.request_delays.append(entry.arguments["timeout"])
        if self.last_retry_timeout is not None:
            self.last_retry_timeout = max(entry.arguments["timeout"], self.last_retry_timeout)
        else:
            self.last_retry_timeout = entry.arguments["timeout"]

    def add_successful_request(self, entry):
        self.requests_successful.append(True)
        delay = time() - entry.arguments["start_time"]
        self.request_delays.append(delay)

    def get_timeout(self):
        if len(self.request_delays) > self.samples_length * 5:
            self._clean_up_data()
        if self.last_retry_timeout is not None:
            timeout = self.last_retry_timeout * 2
        elif len(self.request_delays) < self.samples_length:
            timeout = self.max_timeout * 0.8
        else:
            delays = self.request_delays[-self.samples_length:]
            timeout = mean(delays) * 2 + stdev(delays) * 4
        timeout = max(self.min_timeout, timeout)
        return min(timeout, self.max_timeout)

    def _clean_up_data(self):
        if all(self.requests_successful):
            self.last_retry_timeout = None
        self.requests_successful = self.requests_successful[-self.samples_length:]
        self.request_delays = self.request_delays[-self.samples_length:]
