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


class KnowledgeBase:

    def __init__(self):
        self.__dict__["entries"] = {}

    def __contains__(self, key):
        return key in self.entries

    def __setattr__(self, key, value):
        if key not in self:
            self.entries[key] = value
        else:
            raise AttributeError(key)

    def __getattr__(self, key):
        if key in self:
            return self.entries[key]
        else:
            raise AttributeError(key)
