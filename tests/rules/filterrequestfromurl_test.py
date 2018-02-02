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
    async def test_before_request_allow_request_to_host_matching_filter_in_whitelist(self):
        filter = FilterRequestFromURL(allowed_urls="example.com")

        await filter.before_request(Entry.create("http://example.com/"))

    @async_test()
    async def test_before_request_reject_request_to_host_not_matching_filter_in_whitelist(self):
        filter = FilterRequestFromURL(allowed_urls="example.com")

        with self.assertRaises(RejectRequest):
            await filter.before_request(Entry.create("http://www.example.com/"))

    @async_test()
    async def test_before_request_accept_list_of_url_for_whitelist(self):
        filter = FilterRequestFromURL(allowed_urls=["example.com", "www.example.com", "test.example.com"])
        good_urls = ["http://example.com/", "https://www.example.com/index.php", "http://test.example.com/index.html"]
        bad_urls = ["http://abc.example.com/", "https://example.ca/", "http://www.example.com.net/"]

        for url in bad_urls:
            with self.assertRaises(RejectRequest):
                await filter.before_request(Entry.create(url))
        for url in good_urls:
            await filter.before_request(Entry.create(url))

    @async_test()
    async def test_before_request_allow_request_to_path_matching_filter_in_whitelist(self):
        filter = FilterRequestFromURL(allowed_urls="/allowed")

        await filter.before_request(Entry.create("http://example.com/allowed/index.html"))

    @async_test()
    async def test_before_request_reject_request_to_path_not_matching_filter_in_whitelist(self):
        filter = FilterRequestFromURL(allowed_urls="/allowed")

        with self.assertRaises(RejectRequest):
            await filter.before_request(Entry.create("http://example.com/test/index.html"))

    @async_test()
    async def test_before_request_reject_request_to_path_or_host_not_matching_filter_in_whitelist(self):
        filter = FilterRequestFromURL(allowed_urls="example.com/allowed")

        with self.assertRaises(RejectRequest):
            await filter.before_request(Entry.create("http://example.ca/allowed/index.html"))
        with self.assertRaises(RejectRequest):
            await filter.before_request(Entry.create("http://example.com/test/index.html"))

    @async_test()
    async def test_before_request_allow_request_to_path_and_host_matching_filter_in_whitelist(self):
        filter = FilterRequestFromURL(allowed_urls="example.com/allowed")

        await filter.before_request(Entry.create("http://example.com/allowed/index.html"))

    @async_test()
    async def test_before_request_allow_request_to_host_not_matching_filter_in_blacklist(self):
        filter = FilterRequestFromURL(forbidden_urls="example.com")

        await filter.before_request(Entry.create("http://example.ca/"))

    @async_test()
    async def test_before_request_reject_request_to_host_matching_filter_in_blacklist(self):
        filter = FilterRequestFromURL(forbidden_urls="www.example.com")

        with self.assertRaises(RejectRequest):
            await filter.before_request(Entry.create("http://www.example.com/"))

    @async_test()
    async def test_before_request_accept_list_of_url_for_blacklist(self):
        filter = FilterRequestFromURL(forbidden_urls=["example.com", "www.example.com", "test.example.com"])
        bad_urls = ["http://example.com/", "https://www.example.com/index.php", "http://test.example.com/index.html"]
        good_urls = ["http://abc.example.com/", "https://example.ca/", "http://www.example.com.net/"]

        for url in bad_urls:
            with self.assertRaises(RejectRequest):
                await filter.before_request(Entry.create(url))
        for url in good_urls:
            await filter.before_request(Entry.create(url))

    @async_test()
    async def test_before_request_allow_request_to_path_not_matching_filter_in_blacklist(self):
        filter = FilterRequestFromURL(forbidden_urls="/forbidden")

        await filter.before_request(Entry.create("http://example.com/allowed/index.html"))

    @async_test()
    async def test_before_request_reject_request_to_path_matching_filter_in_blacklist(self):
        filter = FilterRequestFromURL(forbidden_urls="/forbidden")

        with self.assertRaises(RejectRequest):
            await filter.before_request(Entry.create("http://example.com/forbidden/index.html"))

    @async_test()
    async def test_before_request_allow_request_to_path_or_host_not_matching_filter_in_blacklist(self):
        filter = FilterRequestFromURL(forbidden_urls="example.com/forbidden")

        await filter.before_request(Entry.create("http://example.ca/forbidden/index.html"))
        await filter.before_request(Entry.create("http://example.com/test/index.html"))

    @async_test()
    async def test_before_request_reject_request_to_path_and_host_matching_filter_in_blacklist(self):
        filter = FilterRequestFromURL(forbidden_urls="example.com/forbidden")

        with self.assertRaises(RejectRequest):
            await filter.before_request(Entry.create("http://example.com/forbidden/index.html"))

    @async_test()
    async def test_path_matching_only_apply_to_full_directory_name(self):
        filter = FilterRequestFromURL(allowed_urls="example.com/allowed")

        with self.assertRaises(RejectRequest):
            await filter.before_request(Entry.create("http://example.com/allowed-test"))

    def test_constructor_raise_value_error_if_both_domain_list_are_none(self):
        with self.assertRaises(ValueError):
            FilterRequestFromURL(allowed_urls=None, forbidden_urls=None)

    def test_constructor_raise_value_error_if_both_domain_list_are_set(self):
        with self.assertRaises(ValueError):
            FilterRequestFromURL(allowed_urls="example.com", forbidden_urls="test.com")
