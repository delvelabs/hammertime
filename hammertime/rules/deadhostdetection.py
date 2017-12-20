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


from uuid import uuid4
import asyncio

from hammertime.ruleset import HammerTimeException


class DeadHostDetection:

    def __init__(self):
        self.pending_requests = {}
        self.timeout_requests = set()

    def set_kb(self, kb):
        kb.pending_requests = self.pending_requests
        kb.timeout_requests = self.timeout_requests

    async def before_request(self, entry):
        request_id = uuid4()
        entry.arguments["uuid"] = request_id
        self.pending_requests[request_id] = asyncio.Future()

    async def after_headers(self, entry):
        if entry.arguments["uuid"] in self.pending_requests:
            self.pending_requests.pop(entry.arguments["uuid"])

    async def on_timeout(self, entry):
        self.timeout_requests.add(entry.arguments["uuid"])
        if self.pending_requests.keys() == self.timeout_requests:
            raise OfflineHostException()


class OfflineHostException(HammerTimeException):
    pass
