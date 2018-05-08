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
        self.previous_responses = []
        self.max_buffer_size = buffer_size
        self.error_behavior = False
        self.match_threshold = match_threshold
        self.match_filter = match_filter
        self.token_size = token_size

    def set_kb(self, kb):
        kb.behavior_buffer = self.previous_responses

    def load_kb(self, kb):
        self.previous_responses = kb.behavior_buffer

    async def after_response(self, entry):
        if entry.response.code in self.safe_status_codes:
            entry.result.error_behavior = False
            return

        resp_content = self._read_content(entry.response)
        content_simhash = self._hash(resp_content)
        if len(self.previous_responses) >= self.max_buffer_size:
            self.error_behavior = self._is_error_behavior(content_simhash)
            self.previous_responses.pop(0)
        self.previous_responses.append(content_simhash.value)
        entry.result.error_behavior = self.error_behavior

    def _is_error_behavior(self, content_simhash):
        return all(self._responses_match(content_simhash))

    def _hash(self, content):
        return Simhash(content, filter=self.match_filter, token_size=self.token_size)

    def _read_content(self, response):
        return response.raw.decode('utf-8', errors='ignore')

    def _responses_match(self, resp_simhash):
        for simhash_value in self.previous_responses:
            simhash = Simhash(simhash_value)
            yield resp_simhash.distance(simhash) < self.match_threshold


class RejectErrorBehavior:

    async def after_response(self, entry):
        if entry.result.error_behavior:
            raise BehaviorError()


class BehaviorError(RejectRequest):
    pass
