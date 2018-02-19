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
from unittest.mock import MagicMock, patch
from aiohttp.test_utils import make_mocked_coro

from tests.fixtures import async_test
from hammertime.rules import RejectCatchAllRedirect
from hammertime.http import Entry, StaticResponse
from hammertime.ruleset import RejectRequest
from hammertime.kb import KnowledgeBase


class TestRejectCatchAllRedirect(TestCase):

    def setUp(self):
        self.heuristic = RejectCatchAllRedirect()
        self.host = "http://example.com"
        self.fake_engine = MagicMock()
        self.heuristic.set_engine(self.fake_engine)
        self.heuristic.child_heuristics = MagicMock()

    @async_test()
    async def test_after_headers_request_random_filename_in_same_path_as_initial_request_if_response_is_redirect(self):
        self.fake_engine.perform_high_priority = make_mocked_coro(return_value=MagicMock())
        entry0 = self.create_redirected_request("/admin/restricted-resource.php", redirected_to="/admin/login.php")
        entry1 = self.create_redirected_request("/junkpath", redirected_to="/index.html")
        entry2 = self.create_redirected_request("/path/to/admin/resource", redirected_to="/path/to/admin/login.php")

        with patch("hammertime.rules.redirects.uuid4", MagicMock(return_value="uuid")):
            await self.heuristic.after_headers(entry0)
            await self.heuristic.after_headers(entry1)
            await self.heuristic.after_headers(entry2)

            self.assertRequested(self.host + "/admin/uuid", self.fake_engine.perform_high_priority, order=0)
            self.assertRequested(self.host + "/uuid", self.fake_engine.perform_high_priority, order=1)
            self.assertRequested(self.host + "/path/to/admin/uuid", self.fake_engine.perform_high_priority, order=2)

    @async_test()
    async def test_after_headers_doesnt_request_random_filename_if_response_is_not_redirect(self):
        self.fake_engine.perform_high_priority = make_mocked_coro()
        entry = Entry.create("http://example.com/junkpath", response=StaticResponse(404, {}, b"Not found"))

        await self.heuristic.after_headers(entry)

        self.fake_engine.perform_high_priority.assert_not_called()

    @async_test()
    async def test_after_headers_reject_request_if_request_for_random_file_has_same_redirect_as_initial_request(self):
        initial_request = self.create_redirected_request("/admin/resource.php", redirected_to="/admin/login.php")
        returned_entry = self.create_redirected_request("/admin/uuid", redirected_to="/admin/login.php")
        self.fake_engine.perform_high_priority = make_mocked_coro(return_value=returned_entry)

        with self.assertRaises(RejectRequest):
            await self.heuristic.after_headers(initial_request)

    @async_test()
    async def test_after_headers_transform_relative_location_to_absolute_location(self):
        initial_request = self.create_redirected_request("/admin/resource.php", redirected_to="/admin/login.php",
                                                         relative=True)
        returned_entry = self.create_redirected_request("/admin/uuid", redirected_to="/admin/login.php")
        self.fake_engine.perform_high_priority = make_mocked_coro(return_value=returned_entry)

        with self.assertRaises(RejectRequest):
            await self.heuristic.after_headers(initial_request)

    @async_test()
    async def test_before_request_accept_request_if_random_file_not_redirected_to_same_path_as_initial_request(self):
        initial_request = self.create_redirected_request("/admin/resource.php", redirected_to="/admin/login.php")
        returned_entry = self.create_redirected_request("/admin/uuid", redirected_to="/catchAll.html")
        self.fake_engine.perform_high_priority = make_mocked_coro(return_value=returned_entry)

        await self.heuristic.after_headers(initial_request)

    @async_test()
    async def test_after_headers_add_request_response_to_knowledge_base(self):
        first_host = "http://example1.com"
        returned_entry = self.create_redirected_request("/anything", relative=True, redirected_to="/login.php")
        self.fake_engine.perform_high_priority = make_mocked_coro(return_value=returned_entry)
        entry0 = self.create_redirected_request("/admin/restricted-resource.php", host=first_host,
                                                redirected_to="/login.php")
        entry1 = self.create_redirected_request("/junkpath", host=first_host, redirected_to="/login.php")
        entry2 = self.create_redirected_request("/path/to/admin/resource", host=first_host, redirected_to="/login.php")

        second_host = "http://example2.com"
        entry3 = self.create_redirected_request("/admin/restricted-resource.php", host=second_host,
                                                redirected_to="/login.php")
        entry4 = self.create_redirected_request("/junkpath/", host=second_host, redirected_to="/login.php")
        entry5 = self.create_redirected_request("/path/to/admin/resource", host=second_host, redirected_to="/login.php")

        kb = KnowledgeBase()
        self.heuristic.set_kb(kb)

        with patch("hammertime.rules.redirects.uuid4", MagicMock(return_value="uuid")):
            await self.ignore_reject_request(self.heuristic.after_headers, entry0)
            await self.ignore_reject_request(self.heuristic.after_headers, entry1)
            await self.ignore_reject_request(self.heuristic.after_headers, entry2)
            await self.ignore_reject_request(self.heuristic.after_headers, entry3)
            await self.ignore_reject_request(self.heuristic.after_headers, entry4)
            await self.ignore_reject_request(self.heuristic.after_headers, entry5)

            self.assertEqual(kb.redirects["%s/admin/" % first_host], "%s/login.php" % first_host)
            self.assertEqual(kb.redirects["%s/" % first_host], "%s/login.php" % first_host)
            self.assertEqual(kb.redirects["%s/path/to/admin/" % first_host], "%s/login.php" % first_host)
            self.assertEqual(kb.redirects["%s/admin/" % second_host], "%s/login.php" % second_host)
            self.assertEqual(kb.redirects["%s/junkpath/" % second_host], "%s/login.php" % second_host)
            self.assertEqual(kb.redirects["%s/path/to/admin/" % second_host], "%s/login.php" % second_host)

    @async_test()
    async def test_after_headers_doesnt_request_random_filename_if_redirect_is_already_in_knowledge_base(self):
        self.fake_engine.perform_high_priority = make_mocked_coro()
        kb = KnowledgeBase()
        self.heuristic.set_kb(kb)
        kb.redirects["%s/wp-admin/" % self.host] = "%s/somewhere" % self.host

        entry = self.create_redirected_request("/wp-admin/admin.php", redirected_to="/wp-login.php")

        await self.heuristic.after_headers(entry)

        self.fake_engine.perform_high_priority.assert_not_called()

    def create_redirected_request(self, path, *, host=None, redirected_to, relative=False):
        host = host or self.host
        if relative:
            headers = {"location": redirected_to}
        else:
            headers = {"location": host + redirected_to}
        response = StaticResponse(code=302, headers=headers, content=b"content")
        return Entry.create(host + path, response=response)

    def assertRequested(self, url, request_method, order=None):
        requested = False
        if order is not None:
            call_list = [request_method.call_args_list[order]]
        else:
            call_list = request_method.call_args_list
        for call in call_list:
            args, kwargs = call
            entry = args[0]
            if entry.request.url == url:
                requested = True
                break
        self.assertTrue(requested)

    async def ignore_reject_request(self, coro, arg):
        try:
            await coro(arg)
        except RejectRequest:
            pass
