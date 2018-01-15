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
from urllib.parse import urlparse

from hammertime.ruleset import HammerTimeException


class DeadHostDetection:

    def __init__(self, threshold=50):
        self.hosts = {}
        self.threshold = threshold

    def set_kb(self, kb):
        kb.hosts = self.hosts

    async def before_request(self, entry):
        host = self._get_host(entry)
        if host in self.hosts:
            if not self.hosts[host]["pending_requests"].done():
                if self._is_first_attempt(entry):
                    self.hosts[host]["request_count"] += 1
                else:
                    await self.hosts[host]["pending_requests"]
        else:
            self.hosts[host] = {"request_count": 1, "timeout_requests": 0, "pending_requests": asyncio.Future()}

    async def after_headers(self, entry):
        host = self._get_host(entry)
        self.hosts[host]["request_count"] = 0
        self.hosts[host]["timeout_requests"] = 0
        if not self.hosts[host]["pending_requests"].done():
            self.hosts[host]["pending_requests"].set_result(None)

    async def on_timeout(self, entry):
        host = self._get_host(entry)
        self.hosts[host]["timeout_requests"] += 1
        if self.hosts[host]["pending_requests"].done():
            if self.hosts[host]["pending_requests"].exception() is None:
                self.hosts[host]["pending_requests"] = asyncio.Future()
            else:
                raise self.hosts[host]["pending_requests"].exception()

        if self._is_host_dead(host):
            exception = OfflineHostException("%s is offline" % host)
            self.hosts[host]["pending_requests"].set_exception(exception)
            raise exception

    def _get_host(self, entry):
        return urlparse(entry.request.url).netloc

    def _is_first_attempt(self, entry):
        return entry.result.attempt == 1

    def _is_host_dead(self, host):
        timeout_count = self.hosts[host]["timeout_requests"]
        return timeout_count == self.hosts[host]["request_count"] or timeout_count >= self.threshold


class OfflineHostException(HammerTimeException):
    pass
