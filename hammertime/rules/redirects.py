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


from copy import copy
from urllib.parse import urljoin, urlparse
from uuid import uuid4

from hammertime.http import Entry
from hammertime.ruleset import RejectRequest


valid_redirects = (301, 302, 303, 307, 308)


class FollowRedirects:

    def __init__(self, *, max_redirect=15):
        self.max_redirect = max_redirect
        self.engine = None

    def set_engine(self, engine):
        self.engine = engine

    def set_child_heuristics(self, heuristics):
        self.child_heuristics = heuristics

    async def on_request_successful(self, entry):
        status_code = entry.response.code
        if status_code in valid_redirects:
            entry.result.redirects.append(copy(entry))
            await self._follow_redirects(entry)

    async def _follow_redirects(self, entry):
        status_code = entry.response.code
        redirect_count = 0
        while status_code in valid_redirects:
            if redirect_count > self.max_redirect:
                raise RejectRequest("Max redirect limit reached")
            try:
                url = entry.response.headers["location"]
                last_url = entry.result.redirects[-1].request.url
                _entry = await self._perform_request(url, base_url=last_url)
                entry.result.redirects.append(_entry)
                entry.response = _entry.response
                status_code = entry.response.code
                redirect_count += 1
            except KeyError:
                raise RejectRequest("Missing location field in header of redirect")

    async def _perform_request(self, url, base_url):
        entry = Entry.create(urljoin(base_url, url))
        self.engine.stats.requested += 1
        entry = await self.engine.perform(entry, self.child_heuristics)
        self.engine.stats.completed += 1
        return entry


class RejectCatchAllRedirect:

    def __init__(self):
        self.engine = None
        self.redirects = {}

    def set_engine(self, engine):
        self.engine = engine

    def set_kb(self, kb):
        kb.redirects = self.redirects

    def load_kb(self, kb):
        self.redirects = kb.redirects

    def set_child_heuristics(self, heuristics):
        self.child_heuristics = heuristics

    async def after_headers(self, entry):
        if entry.response.code in valid_redirects and "location" in entry.response.headers:
            url = entry.request.url
            path = self._get_url_with_base_path(url)
            random_url = self._build_random_url(path)
            redirect_for_request = self._to_absolute_url(url, entry.response.headers["location"])
            default_redirect_for_path = await self._get_default_redirect_for_path(path, random_url)

            # Some catch-all redirects include the current path in the requested location.
            # Classic examples:
            # - Adding a slash
            # - error.php?src=/origin
            norm_request = self._normalize(redirect_for_request, url)
            norm_default = self._normalize(default_redirect_for_path, random_url)

            if norm_request == norm_default:
                raise RejectRequest("Catch-all redirect rejected: {} redirected to {}".format(
                    url, default_redirect_for_path))

    async def _get_default_redirect_for_path(self, path, random_url):
        if path in self.redirects:
            return self.redirects[path]
        else:
            _entry = await self.engine.perform_high_priority(Entry.create(random_url), self.child_heuristics)
            if _entry.response.code in valid_redirects:
                try:
                    default_redirect = self._to_absolute_url(path, _entry.response.headers["location"])
                    self._add_redirect_to_kb(path, default_redirect)
                    return default_redirect
                except KeyError:
                    pass
            return None

    def _get_url_with_base_path(self, complete_url):
        path = urlparse(complete_url).path
        path_parts = path.split("/")[:-1]
        path = "/".join(path_parts) + "/"
        return urljoin(complete_url, path)

    def _build_random_url(self, base_path):
        random_path = base_path + str(uuid4())
        return random_path

    def _normalize(self, redirect_url, initial_url):
        if redirect_url:
            path = urlparse(initial_url).path
            return redirect_url.replace(path, '_REQUESTED_')
        else:
            return None

    def _add_redirect_to_kb(self, requested_path, redirect_url):
        if requested_path not in self.redirects:
            self.redirects[requested_path] = redirect_url

    def _to_absolute_url(self, base_url, url):
        if urlparse(url).netloc == "":
            return urljoin(base_url, url)
        return url
