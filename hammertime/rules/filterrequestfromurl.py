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
        if regex_blacklist is None and regex_whitelist is None:
            raise ValueError("Need a regex white list or a regex black list.")
        if regex_whitelist is not None and regex_blacklist is not None:
            raise ValueError("Cannot use both a white list and a black list.")
        if regex_whitelist is not None:
            regex_whitelist = self._to_iterable(regex_whitelist)
        self.regex_whitelist = regex_whitelist
        if regex_blacklist is not None:
            regex_blacklist = self._to_iterable(regex_blacklist)
        self.regex_blacklist = regex_blacklist

    async def before_request(self, entry):
        url = entry.request.url
        if self.regex_whitelist:
            if not self._match_found(url, self.regex_whitelist):
                raise RejectRequest("Request URL %s is not in whitelist patterns" % url)
        elif self.regex_blacklist:
            if self._match_found(url, self.regex_blacklist):
                raise RejectRequest("Request URL %s is in blacklist patterns" % url)

    def _to_iterable(self, regex_list):
        if isinstance(regex_list, str):
            return (regex_list,)
        return regex_list

    def _match_found(self, url, regex_list):
        for regex in regex_list:
            if re.search(regex, url):
                return True
        return False
