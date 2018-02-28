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


from unittest import TestCase

import hammertime.rules as rules


class TestHeuristics(TestCase):

    def test_heuristics_define_load_kb_if_using_kb(self):
        for Heuristic in rules.__all__:
            if hasattr(Heuristic, "set_kb"):
                self.assertTrue(hasattr(Heuristic, "load_kb"), msg="%s must define load_kb if using the knowledge "
                                                                   "base." % Heuristic)
