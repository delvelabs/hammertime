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


import re


DEFAULT_FILTER = r'[\w\u4e00-\u9fcc<>]+'

try:
    from simhash import shingle, unsigned_hash, compute, num_differing_bits

    class Simhash:

        def __init__(self, data, filter=DEFAULT_FILTER, token_size=4):
            self.filter = re.compile(filter)
            if isinstance(data, int):
                self.value = data
            else:
                self.value = self.compute(data, token_size)

        def distance(self, hash):
            return num_differing_bits(self.value, hash.value)

        def compute(self, data, token_size):
            content = data.lower()
            content = ''.join(self.filter.findall(content))
            shingles = [''.join(_shingle) for _shingle in shingle(content, token_size)]
            hashes = [unsigned_hash(s.encode("utf-8")) for s in sorted(shingles)]
            return compute(hashes)


except ImportError:
    from simhash import Simhash as _Simhash

    class Simhash(_Simhash):

        def __init__(self, data, filter=DEFAULT_FILTER, token_size=4):
            self.token_size = token_size
            super().__init__(data, reg=filter)

        def _tokenize(self, content):
            content = content.lower()
            content = ''.join(re.findall(self.reg, content))
            tokens = self._slide(content, self.token_size)
            return tokens
