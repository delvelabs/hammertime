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


import copy

from hammertime.http import Entry
from hammertime.ruleset import Heuristics


valid_redirects = (301, 302, 303, 307, 308)


class FollowRedirects:

    def __init__(self, *, max_redirect=15, stats):
        self.max_redirect = max_redirect
        self.engine = None
        self.child_heuristics = Heuristics()
        self.stats = stats

    def set_engine(self, engine):
        self.engine = engine

    async def on_request_successful(self, entry):
        status_code = entry.response.code
        if status_code in valid_redirects:
            entry.result.redirects.append((entry.request, copy.copy(entry.response)))
            await self._follow_redirects(entry)

    async def _follow_redirects(self, entry):
        status_code = entry.response.code
        redirect_count = 0
        while status_code in valid_redirects and redirect_count < self.max_redirect:
            try:
                url = entry.response.headers["location"]
                self.stats.requested += 1
                _entry = await self._perform_request(url)
                entry.result.redirects.append((_entry.request, _entry.response))
                self._replace_response(entry, _entry.response)
                status_code = entry.response.code
                redirect_count += 1
                self.stats.completed += 1
            except KeyError:
                return

    async def _perform_request(self, url):
        entry = Entry.create(url)
        return await self.engine.perform(entry, self.child_heuristics)

    def _replace_response(self, entry, response):
        entry.response.__dict__ = response.__dict__
