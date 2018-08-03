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

import hashlib
from .simhash import Simhash, DEFAULT_FILTER


class ContentHashSampling:

    def __init__(self, hash_method=hashlib.md5):
        self._hash_method = hash_method

    async def after_response(self, entry):
        entry.result.content_hash = self._hash(entry.response)

    def _hash(self, response):
        return self._hash_method(response.raw).digest()


class ContentSimhashSampling:

    def __init__(self, match_filter=DEFAULT_FILTER, token_size=4):
        self.match_filter = match_filter
        self.token_size = token_size

    async def after_response(self, entry):
        entry.result.content_simhash = self._simhash(entry.response)

    def _simhash(self, response):
        try:
            return Simhash(response.content, filter=self.match_filter, token_size=self.token_size)
        except UnicodeDecodeError:  # Response content is not text, store the hash of the raw data:
            return None
