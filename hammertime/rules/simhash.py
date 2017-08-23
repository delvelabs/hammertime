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


try:
    from simhash import shingle, unsigned_hash, compute, num_differing_bits


    class Simhash:

        def __init__(self, data):
            if isinstance(data, int):
                self.value = data
            else:
                self.value = self.compute(data)

        def distance(self, hash):
            return num_differing_bits(self.value, hash.value)

        def compute(self, data):
            window_size = 4
            content = data.lower()
            shingles = [''.join(_shingle) for _shingle in shingle(content, window_size)]
            hashes = [unsigned_hash(s.encode("utf-8")) for s in sorted(shingles)]
            return compute(hashes)


except ImportError:
    from simhash import Simhash as _Simhash


    def Simhash(data):
        return _Simhash(data, reg=".+")
