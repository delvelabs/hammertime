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
import re

from hammertime.rules import FilterRequestFromURL
from hammertime.http import Entry
from hammertime.ruleset import RejectRequest
from tests.fixtures import async_test


class TestFilterRequestFromURL(TestCase):

    def setUp(self):
        pass

    @async_test()
    async def test_before_request_reject_request_with_url_not_in_allowed_domain(self):
        domain = "example.com"
        filter = FilterRequestFromURL(allowed_domain=domain)
        entry = Entry.create("http://example.ca/")

        with self.assertRaises(RejectRequest):
            await filter.before_request(entry)

    @async_test()
    async def test_before_request_allow_request_with_url_in_allowed_domain(self):
        domain = "example.com"
        filter = FilterRequestFromURL(allowed_domain=domain)
        urls = ["http://www.example.com/", "https://example.com/", "http://example.com", "http://svn.example.com/",
                "https://server.example.com/config.php"]

        try:
            for url in urls:
                entry = Entry.create(url)
                await filter.before_request(entry)
        except RejectRequest as e:
            self.fail(str(e))

    @async_test()
    async def test_before_request_reject_request_with_url_in_forbidden_domain(self):
        domain = "forbidden.com"
        filter = FilterRequestFromURL(forbidden_domain=domain)
        entry = Entry.create("http://www.forbidden.com/")

        with self.assertRaises(RejectRequest):
            await filter.before_request(entry)

    @async_test()
    async def test_before_request_works_with_iterable_for_allowed_domain(self):
        domain_list = ["www.example.com", "dev.example.com", "test.example.com"]
        ok_urls = ["http://www.example.com/", "https://dev.example.com/index.html", "http://1.test.example.com/abc.php"]
        bad_urls = ["http://svn.example.com/", "https://server.example.com/config.php", "https://abc.example.com/",
                    "http://example.com/", "http://www.example.com.unrelated-domain.test/"]
        filter = FilterRequestFromURL(allowed_domain=domain_list)

        for url in bad_urls:
            with self.assertRaises(RejectRequest):
                await filter.before_request(Entry.create(url))

        try:
            for url in ok_urls:
                await filter.before_request(Entry.create(url))
        except RejectRequest as e:
            self.fail(str(e))

    @async_test()
    async def test_before_request_works_with_iterable_for_forbidden_domain(self):
        domain_list = ["server.example.com", "abc.example.com", "svn.example.com"]
        ok_urls = ["http://www.example.com/", "https://example.com/", "http://example.com",
                   "https://dev.example.com/index.html", "http://1.test.example.com/abc.php",
                   "http://abc.example.com.test"]
        bad_urls = ["http://svn.example.com/", "https://server.example.com/config.php", "https://abc.example.com/"]
        filter = FilterRequestFromURL(forbidden_domain=domain_list)

        for url in bad_urls:
            with self.assertRaises(RejectRequest):
                await filter.before_request(Entry.create(url))

        try:
            for url in ok_urls:
                await filter.before_request(Entry.create(url))
        except RejectRequest as e:
            self.fail(str(e))

    def test_constructor_raise_value_error_if_both_domain_list_are_none(self):
        with self.assertRaises(ValueError):
            FilterRequestFromURL(allowed_domain=None, forbidden_domain=None)

    def test_constructor_raise_value_error_if_both_domain_list_are_set(self):
        with self.assertRaises(ValueError):
            FilterRequestFromURL(allowed_domain="example.com", forbidden_domain="test.com")
