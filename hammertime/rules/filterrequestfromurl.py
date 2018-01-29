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

from hammertime.ruleset import RejectRequest


class FilterRequestFromURL:

    def __init__(self, *, whitelist_regex=None, blacklist_regex=None):
        self.whitelist_regex = whitelist_regex
        self.blacklist_regex = blacklist_regex

    async def before_request(self, entry):
        if self.whitelist_regex is not None:
            if not re.search(self.whitelist_regex, entry.request.url):
                raise RejectRequest("Request URL %s is not in whitelist patterns" % entry.request.url)
        elif self.blacklist_regex is not None:
            if re.search(self.blacklist_regex, entry.request.url):
                raise RejectRequest("Request URL %s is in blacklist patterns" % entry.request.url)
