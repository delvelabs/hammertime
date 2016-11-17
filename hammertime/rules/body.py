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


from ..ruleset import IgnoreBody
from statistics import mean, stdev
import logging


logger = logging.getLogger(__name__)


class IgnoreLargeBody:

    def __init__(self, initial_limit=1024*1024):
        self.initial_limit = initial_limit
        self.data = BodySize(self.initial_limit)

    def set_kb(self, kb):
        kb.body_size = self.data

    async def after_headers(self, entry):
        length = entry.response.headers.get('Content-Length')
        if length is not None:
            try:
                length = int(length)
                self.data.add(length)
                if length > self.data.applicable_limit:
                    raise IgnoreBody()
            except ValueError:
                logger.debug("Bad Content-Length: %s", length)


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
                self.calculated_limit = mean(self.collected_sizes) + 5 * stdev(self.collected_sizes)
                logger.info("Updating max body size to %s", self.calculated_limit)
