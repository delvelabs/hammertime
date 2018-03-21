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


from statistics import mean, stdev
import logging


logger = logging.getLogger(__name__)


class IgnoreLargeBody:

    def __init__(self, initial_limit=1024*1024):
        self.initial_limit = initial_limit
        self.data = BodySize(self.initial_limit)

    def set_kb(self, kb):
        kb.body_size = self.data

    def load_kb(self, kb):
        self.data = kb.body_size

    async def after_headers(self, entry):
        entry.result.read_length = self._get_read_limit(entry.response)

    async def after_response(self, entry):
        if entry.result.read_length == -1:
            # Collect statistics post-response when the content-length was unknown.
            full_length = len(entry.response.raw)
            limit = self.data.applicable_limit
            self.data.add(full_length)

            if full_length > limit:
                # Apply the limit post-response if above the desired limit
                # Keep read_length coherent with the content for other heuristics to
                # work from.
                entry.response.raw = entry.response.raw[0:limit]
                entry.response.truncated = True
                entry.result.read_length = limit

    def _get_read_limit(self, response):
        length = response.headers.get('Content-Length')
        if length is not None:
            try:
                length = int(length)
                self.data.add(length)
                return self.data.applicable_limit
            except ValueError:
                logger.debug("Bad Content-Length: %s", length)

        return self.data.calculated_limit or -1


class BodySize:

    def __init__(self, initial_limit):
        self.initial_limit = initial_limit
        self.collected_sizes = []
        self.calculated_limit = None

    @property
    def applicable_limit(self):
        return self.calculated_limit or self.initial_limit

    def add(self, length):
        if self.calculated_limit is None:
            self.collected_sizes.append(length)

            if len(self.collected_sizes) > 500:
                self.calculated_limit = int(mean(self.collected_sizes) + 5 * stdev(self.collected_sizes))
                logger.info("Updating max body size to %s", self.calculated_limit)
