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

    def __init__(self):
        self.hosts = {}

    def set_kb(self, kb):
        kb.hosts = self.hosts

    async def before_request(self, entry):
        host = urlparse(entry.request.url).netloc
        if host in self.hosts:
            if not self.hosts[host]["is_done"].done():
                if entry.result.attempt == 1:
                    self.hosts[host]["request_count"] += 1
                else:
                    await self.hosts[host]["is_done"]
        else:
            self.hosts[host] = {"request_count": 1, "timeout_requests": 0, "is_done": asyncio.Future()}

    async def after_headers(self, entry):
        host = urlparse(entry.request.url).netloc
        self.hosts[host]["request_count"] = 0
        if not self.hosts[host]["is_done"].done():
            self.hosts[host]["is_done"].set_result(None)

    async def on_timeout(self, entry):
        host = urlparse(entry.request.url).netloc
        if not self.hosts[host]["is_done"].done():
            self.hosts[host]["timeout_requests"] += 1
            if self.hosts[host]["timeout_requests"] == self.hosts[host]["request_count"]:
                exception = OfflineHostException("%s is offline" % host)
                self.hosts[host]["is_done"].set_exception(exception)
                raise exception


class OfflineHostException(HammerTimeException):
    pass
