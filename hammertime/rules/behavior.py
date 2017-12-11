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
from hammertime.rules.simhash import Simhash


class DetectBehaviorChange:

    def __init__(self, buffer_size=5):
        self.response_buffer = []
        self.max_buffer_size = buffer_size
        self.error_behavior = False

    def set_kb(self, kb):
        kb.behavior_buffer = self.response_buffer

    async def after_response(self, entry):
        if len(self.response_buffer) >= self.max_buffer_size:
            self.error_behavior = self._test_behavior(entry.response.content)
            self.response_buffer.pop(0)
        self.response_buffer.append(entry.response.content)
        if self.error_behavior:
            raise BehaviorChanged()

    def _test_behavior(self, content):
        return all(self._hash(_content).distance(self._hash(content)) < 5 for _content in self.response_buffer)

    def _hash(self, content):
        return Simhash(content)


class BehaviorChanged(HammerTimeException):
    pass
