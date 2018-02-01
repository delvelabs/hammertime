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
from urllib.parse import urlparse

from hammertime.ruleset import RejectRequest


class FilterRequestFromURL:

    def __init__(self, *, allowed_domain=None, forbidden_domain=None):
        if forbidden_domain is None and allowed_domain is None:
            raise ValueError("Need a domain white list or a domain black list.")
        if allowed_domain is not None and forbidden_domain is not None:
            raise ValueError("Cannot use both a white list and a black list.")
        if allowed_domain is not None:
            allowed_domain = self._parse_domain_list(allowed_domain)
        self.allowed_domain = allowed_domain
        if forbidden_domain is not None:
            forbidden_domain = self._parse_domain_list(forbidden_domain)
        self.forbidden_domain = forbidden_domain

    async def before_request(self, entry):
        url = urlparse(entry.request.url)
        if self.allowed_domain:
            if not self._match_found(url.netloc, self.allowed_domain):
                raise RejectRequest("Request URL %s is not in whitelist patterns" % url.geturl())
        elif self.forbidden_domain:
            if self._match_found(url.netloc, self.forbidden_domain):
                raise RejectRequest("Request URL %s is in blacklist patterns" % url.geturl())

    def _parse_domain_list(self, domain_list):
        if isinstance(domain_list, str):
            return [self._split_domain_in_parts(domain_list)]
        else:
            parsed = []
            for domain in domain_list:
                parsed.append(self._split_domain_in_parts(domain))
        return parsed

    def _split_domain_in_parts(self, domain):
        parts = []
        for part in reversed(domain.split(".")):
            parts.append(part)
        return parts

    def _match_found(self, netloc, domain_list):
        parsed = self._split_domain_in_parts(netloc)
        for domain_parts in domain_list:
            if self._domain_contains(domain_parts, parsed):
                return True
        return False

    def _domain_contains(self, container_domain_parts, contained_domain_parts):
        if len(container_domain_parts) > len(contained_domain_parts):
            return False
        for i in range(len(container_domain_parts)):
            if container_domain_parts[i] != contained_domain_parts[i]:
                return False
        return True
