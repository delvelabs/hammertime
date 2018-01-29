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

    def __init__(self, *, regex_whitelist=None, regex_blacklist=None):
        if regex_whitelist is not None:
            regex_whitelist = (regex_whitelist,) if isinstance(regex_whitelist, str) else regex_whitelist
        self.regex_whitelist = regex_whitelist
        if regex_blacklist is not None:
            regex_blacklist = (regex_blacklist,) if isinstance(regex_blacklist, str) else regex_blacklist
        self.regex_blacklist = regex_blacklist

    async def before_request(self, entry):
        if self.regex_whitelist:
            for regex in self.regex_whitelist:
                if re.search(regex, entry.request.url):
                    return
            raise RejectRequest("Request URL %s is not in whitelist patterns" % entry.request.url)
        elif self.regex_blacklist:
            for regex in self.regex_blacklist:
                if re.search(regex, entry.request.url):
                    raise RejectRequest("Request URL %s is in blacklist patterns" % entry.request.url)
