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


from ..ruleset import RejectRequest


class RejectStatusCode:

    def __init__(self, *args):
        self.reject_set = set()
        for r in args:
            self.reject_set |= set(r)

    async def after_headers(self, entry):
        if entry.response.code in self.reject_set:
            raise RejectRequest("Status code reject: %s" % entry.response.code)
