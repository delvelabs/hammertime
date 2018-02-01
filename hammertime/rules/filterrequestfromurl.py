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
            allowed_domain = self._parse_url_list(allowed_domain)
        self.allowed_domain = allowed_domain
        if forbidden_domain is not None:
            forbidden_domain = self._parse_url_list(forbidden_domain)
        self.forbidden_domain = forbidden_domain

    async def before_request(self, entry):
        url = entry.request.url
        if self.allowed_domain:
            if not self._match_found(url, self.allowed_domain):
                raise RejectRequest("Request URL %s is not in whitelist patterns" % url)
        elif self.forbidden_domain:
            if self._match_found(url, self.forbidden_domain):
                raise RejectRequest("Request URL %s is in blacklist patterns" % url)

    def _parse_url_list(self, urls):
        if isinstance(urls, str):
            return [self._parse_url(urls)]
        filters = []
        for url in urls:
            filters.append(self._parse_url(url))
        return filters

    def _parse_url(self, url):
        filter = {}
        if "//" not in url and url[0] != "/":
            url = "//" + url  # without this example.com/index.html is seen as a relative path.
        parsed_url = urlparse(url)
        if len(parsed_url.netloc) > 0:
            filter["domain"] = self._split_domain_in_parts(parsed_url.netloc)
        if len(parsed_url.path) > 0:
            filter["path"] = self._split_path_in_parts(parsed_url.path)
        return filter

    def _split_domain_in_parts(self, domain):
        parts = []
        for part in reversed(domain.split(".")):
            parts.append(part)
        return parts

    def _split_path_in_parts(self, path):
        return [part for part in path.split("/") if len(part) > 0]

    def _match_found(self, url, filter_list):
        parsed = urlparse(url)
        for filter in filter_list:
            domain_match = False
            path_match = False
            if "domain" in filter:
                netloc = self._split_domain_in_parts(parsed.netloc)
                if self._domain_contains(filter["domain"], netloc):
                    domain_match = True
            if "path" in filter:
                path = self._split_path_in_parts(parsed.path)
                if self._path_contains(filter["path"], path):
                    path_match = True
            if "domain" in filter and "path" in filter:
                if domain_match and path_match:
                    return True
            elif domain_match or path_match:
                return True
        return False

    def _domain_contains(self, container_domain_parts, contained_domain_parts):
        if len(container_domain_parts) > len(contained_domain_parts):
            return False
        for i in range(len(container_domain_parts)):
            if container_domain_parts[i] != contained_domain_parts[i]:
                return False
        return True

    def _path_contains(self, container_path_parts, contained_path_parts):
        if len(container_path_parts) > len(contained_path_parts):
            return False
        for i in range(len(container_path_parts)):
            if container_path_parts[i] != contained_path_parts[i]:
                return False
        return True
