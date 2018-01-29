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

from hammertime.rules import FilterRequestFromURL
from hammertime.http import Entry
from hammertime.ruleset import RejectRequest
from tests.fixtures import async_test


class TestFilterRequestFromURL(TestCase):

    def setUp(self):
        pass

    @async_test()
    async def test_before_request_reject_request_not_matching_whitelist_regex(self):
        whitelist_regex = "http://(?:\w+\.)*example.com"
        filter = FilterRequestFromURL(whitelist_regex=whitelist_regex)
        entry = Entry.create("http://external-website.com/")

        with self.assertRaises(RejectRequest):
            await filter.before_request(entry)

    @async_test()
    async def test_before_request_allow_request_matching_whitelist_regex(self):
        whitelist_regex = "(?:\w+\.)*example.com"
        filter = FilterRequestFromURL(whitelist_regex=whitelist_regex)
        urls = ["http://www.example.com/", "https://example.com/", "http://example.com", "http://svn.example.com/",
                "https://server.example.com/config.php"]

        try:
            for url in urls:
                entry = Entry.create(url)
                await filter.before_request(entry)
        except RejectRequest as e:
            self.fail(str(e))

    @async_test()
    async def test_before_request_reject_request_matching_blacklist_regex(self):
        blacklist_regex = "(?:\w+\.)*dont-touch-this-server.com"
        filter = FilterRequestFromURL(blacklist_regex=blacklist_regex)
        entry = Entry.create("http://www.dont-touch-this-server.com/")

        with self.assertRaises(RejectRequest):
            await filter.before_request(entry)
