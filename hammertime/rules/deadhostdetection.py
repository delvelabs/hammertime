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


from urllib.parse import urlparse

from hammertime.ruleset import RejectRequest


class DeadHostDetection:

    def __init__(self, threshold=50):
        self.hosts = {}
        self.dead_hosts = []
        self.threshold = threshold

    def set_kb(self, kb):
        kb.dead_hosts = self.dead_hosts

    def load_kb(self, kb):
        self.dead_hosts = kb.dead_hosts

    async def before_request(self, entry):
        host = self._get_host(entry)
        if host not in self.hosts:
            self.hosts[host] = {"timeout_requests": 0}
        elif host in self.dead_hosts:
            raise OfflineHostException("%s is offline" % host)

    async def after_headers(self, entry):
        self.hosts[self._get_host(entry)]["timeout_requests"] = 0

    async def on_timeout(self, entry):
        host = self._get_host(entry)
        self.hosts[host]["timeout_requests"] += 1
        if host in self.dead_hosts or self._is_host_dead(host):
            raise OfflineHostException("%s is offline" % host)

    async def on_host_unreachable(self, entry):
        await self.on_timeout(entry)

    def _get_host(self, entry):
        return urlparse(entry.request.url).netloc

    def _is_host_dead(self, host):
        if self.hosts[host]["timeout_requests"] >= self.threshold:
            self.dead_hosts.append(host)
            return True
        else:
            return False


class OfflineHostException(RejectRequest):
    pass
