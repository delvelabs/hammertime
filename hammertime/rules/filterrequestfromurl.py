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


from urllib.parse import urlparse

from hammertime.ruleset import RejectRequest


class FilterRequestFromURL:

    def __init__(self, *, allowed_urls=None, forbidden_urls=None):
        if forbidden_urls is None and allowed_urls is None:
            raise ValueError("Need an URL white list or an URL black list.")
        if allowed_urls is not None and forbidden_urls is not None:
            raise ValueError("Cannot use both a white list and a black list.")

        if allowed_urls is not None:
            allowed_urls = self._parse_url_list(allowed_urls)
        self.allowed_filters = allowed_urls

        if forbidden_urls is not None:
            forbidden_urls = self._parse_url_list(forbidden_urls)
        self.forbidden_filters = forbidden_urls

    async def before_request(self, entry):
        url = entry.request.url
        if self.allowed_filters:
            if not self._match_found(url, self.allowed_filters):
                raise RejectRequest("Request URL %s is not in URL whitelist" % url)
        elif self.forbidden_filters:
            if self._match_found(url, self.forbidden_filters):
                raise RejectRequest("Request URL %s is in URL blacklist" % url)

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
            url = "//" + url  # without this 'example.com/index.html' is seen as a relative path.
        parsed_url = urlparse(url)
        if len(parsed_url.netloc) > 0:
            filter["netloc"] = parsed_url.netloc
        if len(parsed_url.path) > 0:
            filter["path"] = parsed_url.path
        return filter

    def _match_found(self, url, filter_list):
        parsed = urlparse(url)
        for filter in filter_list:
            if self._apply_filter(parsed, filter):
                return True
        return False

    def _apply_filter(self, parsed_url, filter):
        for key in filter.keys():
            if filter[key] != getattr(parsed_url, key):
                return False
        return True
