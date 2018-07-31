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

from hammertime.ruleset import RejectRequest
from hammertime.rules.simhash import Simhash, DEFAULT_FILTER


class DetectBehaviorChange:

    def __init__(self, buffer_size=10, match_threshold=5, match_filter=DEFAULT_FILTER, token_size=4,
                 safe_status_codes=None):
        self.safe_status_codes = safe_status_codes or {401, 403, 404}
        self.behavior_buffer = []
        self.known_bad_behavior = set()
        self.max_buffer_size = buffer_size
        self.error_behavior = False
        self.match_threshold = match_threshold
        self.match_filter = match_filter
        self.token_size = token_size

    def set_kb(self, kb):
        kb.bad_behavior_response = self.known_bad_behavior

    def load_kb(self, kb):
        self.known_bad_behavior = kb.bad_behavior_response

    async def after_response(self, entry):
        if entry.response.code in self.safe_status_codes:
            entry.result.error_behavior = False
            return

        resp_content = self._read_content(entry.response)
        content_simhash = self._hash(resp_content)
        entry.result.error_simhash = content_simhash.value

        if any(content_simhash.distance(Simhash(known)) < self.match_threshold for known in self.known_bad_behavior):
            entry.result.error_behavior = True
            return

        if len(self.behavior_buffer) >= self.max_buffer_size:
            self.error_behavior = self._is_error_behavior(content_simhash)
            self.behavior_buffer.pop(0)

        if self.error_behavior:
            for x in self.behavior_buffer:
                self.known_bad_behavior.add(x)

        self.behavior_buffer.append(content_simhash.value)
        entry.result.error_behavior = self.error_behavior

    def _is_error_behavior(self, content_simhash):
        return all(self._responses_match(content_simhash))

    def _hash(self, content):
        return Simhash(content, filter=self.match_filter, token_size=self.token_size)

    def _read_content(self, response):
        return response.raw.decode('utf-8', errors='ignore')

    def _responses_match(self, resp_simhash):
        for simhash_value in self.behavior_buffer:
            simhash = Simhash(simhash_value)
            yield resp_simhash.distance(simhash) < self.match_threshold


class BehaviorError(RejectRequest):
    pass


class RejectErrorBehavior:

    def __init__(self, error_class=BehaviorError):
        self.error_class = error_class

    async def after_response(self, entry):
        if entry.result.error_behavior:
            raise self.error_class("Error behavior detected")
