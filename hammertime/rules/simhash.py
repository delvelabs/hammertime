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
import hashlib


try:
    raise ImportError
    from simhash import shingle, unsigned_hash, compute, num_differing_bits


    class Simhash:

        def __init__(self, data):
            self.data = data

        def distance(self, hash):
            return num_differing_bits(self.compute(), hash.compute())

        def compute(self):
            window_size = 4
            content = self.data.lower()
            shingles = [''.join(_shingle) for _shingle in shingle(content, window_size)]
            hashes = [unsigned_hash(s.encode("utf-8")) for s in sorted(shingles)]
            return compute(hashes)


except ImportError:

    class Simhash:

        def __init__(self, value, reg='.+'):
            self.fingerprints_size = 64
            self.reg = reg
            self._compute(value)

        def _slide(self, content, width=4):
            return [content[i:i + width] for i in range(max(len(content) - width + 1, 1))]

        def _tokenize(self, data):
            data = data.lower()
            data = ''.join(re.findall(self.reg, data))
            tokens = self._slide(data)
            return tokens

        def _compute(self, value):
            tokens = self._tokenize(value)
            result_vector = [0] * self.fingerprints_size
            for token in tokens:
                _hash = self.hash(token.encode("utf-8"))
                for i in range(self.fingerprints_size):
                    result_vector[i] += 1 if _hash & (1 << i) else -1
            self.value = 0
            for i in range(self.fingerprints_size):
                if result_vector[i] > 0:
                    self.value |= (1 << i)

        def distance(self, another):
            if self.fingerprints_size != another.fingerprints_size:
                return False
            distance = 0
            diff_bit = self.value ^ another.value
            for i in range(self.fingerprints_size):
                mask = 1 << i
                if diff_bit & mask != 0:
                    distance += 1
            return distance

        def hash(self, data):
            # The c++ implementation uses the first 8 most significant bytes of the hash, so we do the same.
            return int(hashlib.md5(data).hexdigest()[0:16], 16)
