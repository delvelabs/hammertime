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

from hammertime.ruleset import HammerTimeException
from hammertime.rules.simhash import Simhash, DEFAULT_FILTER


class DetectBehaviorChange:

    def __init__(self, buffer_size=10, match_threshold=5, match_filter=DEFAULT_FILTER, token_size=4):
        self.response_simhash_buffer = []
        self.max_buffer_size = buffer_size
        self.error_behavior = False
        self.match_threshold = match_threshold
        self.match_filter = match_filter
        self.token_size = token_size

    def set_kb(self, kb):
        kb.behavior_buffer = self.response_simhash_buffer

    async def after_response(self, entry):
        if len(self.response_simhash_buffer) >= self.max_buffer_size:
            self.error_behavior = self._is_error_behavior(entry)
            self.response_simhash_buffer.pop(0)
        self.response_simhash_buffer.append(self._hash(self._read_content(entry.response)).value)
        if self.error_behavior:
            raise BehaviorChanged()

    def _is_error_behavior(self, entry):
        content = self._read_content(entry.response)
        content_simhash = self._hash(content)
        return all(self._compare_simhash(self._hash(value), content_simhash) for value in self.response_simhash_buffer)

    def _hash(self, content):
        return Simhash(content, filter=self.match_filter, token_size=self.token_size)

    def _read_content(self, response):
        return response.raw.decode('utf-8', errors='ignore')

    def _compare_simhash(self, simhash0, simhash1):
        return simhash0.distance(simhash1) < self.match_threshold


class BehaviorChanged(HammerTimeException):
    pass
