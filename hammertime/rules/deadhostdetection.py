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

    def __init__(self, threshold=50, wait_time=0.5):
        self.hosts = {}
        self.dead_hosts = []
        self.threshold = threshold
        self.wait_time = wait_time

    def set_kb(self, kb):
        kb.dead_hosts = self.dead_hosts

    async def before_attempt(self, entry):
        host = self._get_host(entry)
        if self._is_first_request_to_host(host):
            self.hosts[host] = {"request_count": 1, "timeout_requests": 0, "possibly_dead": True}
        elif host in self.dead_hosts:
            raise OfflineHostException("%s is offline" % host)
        else:
            if self._is_possibly_dead(host):
                if self._is_first_attempt(entry):
                    self.hosts[host]["request_count"] += 1
                else:
                    await asyncio.sleep(self.wait_time)

    async def before_request(self, entry):
        host = self._get_host(entry)
        if host in self.dead_hosts:
            raise OfflineHostException("%s is offline" % host)

    async def after_headers(self, entry):
        host = self._get_host(entry)
        self._on_host_response(host)

    async def on_timeout(self, entry):
        host = self._get_host(entry)
        self.hosts[host]["timeout_requests"] += 1
        if host in self.dead_hosts:
            raise OfflineHostException("%s is offline" % host)
        elif self._is_host_dead(host):
            self.dead_hosts.append(host)
            raise OfflineHostException("%s is offline" % host)
        else:
            self.hosts[host]["possibly_dead"] = True

    async def on_error(self, entry):
        host = self._get_host(entry)
        self._on_host_response(host)

    def _on_host_response(self, host):
        self.hosts[host]["request_count"] = 0
        self.hosts[host]["timeout_requests"] = 0
        self.hosts[host]["possibly_dead"] = False

    def _get_host(self, entry):
        return urlparse(entry.request.url).netloc

    def _is_first_attempt(self, entry):
        return entry.result.attempt == 1

    def _is_host_dead(self, host):
        timeout_count = self.hosts[host]["timeout_requests"]
        return timeout_count == self.hosts[host]["request_count"] or timeout_count >= self.threshold

    def _is_first_request_to_host(self, host):
        return host not in self.hosts

    def _is_possibly_dead(self, host):
        if host in self.hosts:
            return self.hosts[host]["possibly_dead"]
        else:
            return False


class OfflineHostException(HammerTimeException):
    pass
