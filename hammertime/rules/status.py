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
from difflib import SequenceMatcher


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
            "/%s.txt",
            "/%s.js",
            "/.%s",
        ]

        self.performed = {}
        self.results = {}

    def set_engine(self, engine):
        self.engine = engine

    def set_kb(self, kb):
        kb.page_not_found_response = self.results

    async def after_response(self, entry):
        lock = urljoin(entry.request.url, "/")

        if lock not in self.performed:
            # Temporarily assign a future to make sure work is not done twice
            self.performed[lock] = asyncio.Future()

            responses = await self._collect_samples(entry)
            self.results[lock] = responses
            self.performed[lock].set_result(True)

            # Remove the wait lock
            self.performed[lock] = None
        elif self.performed[lock] is not None:
            await self.performed[lock]

        if len(entry.response.content) == 0:
            raise RejectRequest("Request is a false 404.")

        url_pattern = self._get_pattern_from_url(entry.request.url)
        for result in self.results[lock]:
            if result["pattern"] == url_pattern:
                if result["code"] == entry.response.code and self._content_match(entry.response.content, result["content"]):
                    raise RejectRequest("Request is a false 404.")

    async def _collect_samples(self, entry):
        targets = [Entry.create(urljoin(entry.request.url, pattern % self.random_token), arguments={"pattern": pattern})
                   for pattern in self.patterns]
        jobs = [self.engine.perform_high_priority(entry, self.child_heuristics) for entry in targets]
        results = await asyncio.gather(*jobs)
        responses = []
        for entry in results:
            responses.append({"pattern": entry.arguments["pattern"], "code": entry.response.code,
                              "content": entry.response.content})
        return responses

    def _get_pattern_from_url(self, url):
        path = url[len(urljoin(url, "/")):]
        replace_path = path[:path.index(".")] if "." in path else path
        for pattern in self.patterns:
            if pattern % replace_path == "/%s" % path:
                return pattern
        return None

    def _content_match(self, response_content, soft_404_content):
        matcher = SequenceMatcher(a=response_content, b=soft_404_content, autojunk=False)
        return matcher.ratio() > 0.8
