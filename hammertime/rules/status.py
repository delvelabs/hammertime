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


class DetectSoft404:

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
        self.soft_404_responses = {}

    def set_engine(self, engine):
        self.engine = engine

    def set_kb(self, kb):
        kb.soft_404_responses = self.soft_404_responses

    async def after_response(self, entry):
        server_address = urljoin(entry.request.url, "/")

        if server_address not in self.performed:
            # Temporarily assign a future to make sure work is not done twice
            self.performed[server_address] = asyncio.Future()

            responses = await self._collect_samples(entry)
            self.soft_404_responses[server_address] = responses
            self.performed[server_address].set_result(True)

            # Remove the wait lock
            self.performed[server_address] = None
        elif self.performed[server_address] is not None:
            await self.performed[server_address]

        if entry.request.url == server_address:
            return

        if len(entry.response.content) == 0:
            raise RejectRequest("Request is a soft 404.")

        url_pattern = self._get_pattern_from_url(entry.request.url)
        if url_pattern is not None:
            for result in self.soft_404_responses[server_address]:
                if result["pattern"] == url_pattern:
                    if result["code"] == entry.response.code and self._content_match(entry.response.content, result["content"]):
                        raise RejectRequest("Request is a soft 404.")
        else:
            for result in self.soft_404_responses[server_address]:
                if result["code"] == entry.response.code and self._content_match(entry.response.content, result["content"]):
                    raise RejectRequest("Request is a soft 404.")

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
        if path.startswith("."):
            return "/.%s"
        elif path.endswith("/"):
            return "/%s/"
        elif "." not in path:
            return "/%s"

        replace_path = path[:path.rindex(".")]
        for pattern in self.patterns:
            if pattern % replace_path == "/%s" % path:
                return pattern
        return None

    def _content_match(self, response_content, soft_404_content):
        matcher = SequenceMatcher(a=response_content, b=soft_404_content, autojunk=False)
        return matcher.ratio() > 0.8
