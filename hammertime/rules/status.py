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
import uuid
from urllib.parse import urljoin

from ..ruleset import RejectRequest, Heuristics
from ..http import Entry


class RejectStatusCode:

    def __init__(self, *args):
        self.reject_set = set()
        for r in args:
            self.reject_set |= set(r)

    async def after_headers(self, entry):
        if entry.response.code in self.reject_set:
            raise RejectRequest("Status code reject: %s" % entry.response.code)


class DetectFalse404:

    def __init__(self):
        self.engine = None
        self.random_token = str(uuid.uuid4())
        self.child_heuristics = Heuristics()
        self.patterns = [
            "/%s",
            "/%s/",
            "/%s.html",
            "/%s.php",
            "/%s.asp",
            "/%s.aspx",
            "/%s.pl",
            "/%s.cgi",
            "/%s.cfm",
            "/.%s",
        ]

        self.performed = {}

    def set_engine(self, engine):
        self.engine = engine

    async def after_response(self, entry):
        lock = urljoin(entry.request.url, "/")

        if lock not in self.performed:
            # Temporarily assign a future to make sure work is not done twice
            self.performed[lock] = asyncio.Future()

            await self._collect_samples(entry)
            self.performed[lock].set_result(True)

            # Remove the wait lock
            self.performed[lock] = None
        elif self.performed[lock] is not None:
            await self.performed[lock]

    async def _collect_samples(self, entry):
        targets = {urljoin(entry.request.url, pattern % self.random_token) for pattern in self.patterns}

        jobs = [self.engine.perform_high_priority(Entry.create(target), self.child_heuristics) for target in targets]
        results = await asyncio.gather(*jobs)
