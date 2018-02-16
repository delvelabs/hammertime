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


class TestRejectCatchAllRedirect(TestCase):

    @async_test()
    async def test_before_request_fetch_same_path_as_origin_request_with_random_filename(self):
        reject = RejectCatchAllRedirect()
        fake_engine = MagicMock()
        fake_engine.perform_high_priority = make_mocked_coro(return_value=MagicMock())
        reject.set_engine(fake_engine)
        entry0 = Entry.create("http://example.com/admin/login.php")
        entry1 = Entry.create("http://example.com/index.html")
        entry2 = Entry.create("http://example.com/path/to/admin/login.php")

        with patch("hammertime.rules.rejectredirects.uuid4", MagicMock(return_value="uuid")):
            await reject.before_request(entry0)
            await reject.before_request(entry1)
            await reject.before_request(entry2)

            self.assertRequested("http://example.com/admin/uuid", fake_engine.perform_high_priority, order=0)
            self.assertRequested("http://example.com/uuid", fake_engine.perform_high_priority, order=1)
            self.assertRequested("http://example.com/path/to/admin/uuid", fake_engine.perform_high_priority, order=2)

    @async_test()
    async def test_before_request_raise_reject_request_if_random_file_redirect_to_origin_request(self):
        reject = RejectCatchAllRedirect()
        fake_engine = MagicMock()
        response = StaticResponse(302, {"location": "http://example.com/admin/login.php"}, b"content")
        returned_entry = Entry.create("http://example.com/admin/uuid", response=response)
        fake_engine.perform_high_priority = make_mocked_coro(return_value=returned_entry)
        reject.set_engine(fake_engine)
        entry = Entry.create("http://example.com/admin/login.php")

        with self.assertRaises(RejectRequest):
            await reject.before_request(entry)

    @async_test()
    async def test_before_request_accept_request_if_random_file_not_redirected_to_origin_request(self):
        reject = RejectCatchAllRedirect()
        fake_engine = MagicMock()
        response = StaticResponse(302, {"location": "http://example.com/catchAll.html"}, b"content")
        returned_entry = Entry.create("http://example.com/admin/uuid", response=response)
        fake_engine.perform_high_priority = make_mocked_coro(return_value=returned_entry)
        reject.set_engine(fake_engine)
        entry = Entry.create("http://example.com/admin/login.php")

        await reject.before_request(entry)

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
