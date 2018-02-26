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

from hammertime.rules import RejectSoft404
from hammertime.ruleset import RejectRequest
from hammertime.http import Entry
from tests.fixtures import async_test


class TestRejectSoft404(TestCase):

    @async_test()
    async def test_after_response_raise_reject_request_if_entry_is_flagged_as_soft404(self):
        reject_soft404 = RejectSoft404()
        entry = Entry.create("http://example.com/junk.html")
        entry.result.soft404 = True

        with self.assertRaises(RejectRequest):
            await reject_soft404.after_response(entry)

    @async_test()
    async def test_after_response_does_not_raise_if_entry_is_not_flagged_as_soft404(self):
        reject_soft404 = RejectSoft404()
        entry = Entry.create("http://example.com/junk.html")
        entry.result.soft404 = False

        await reject_soft404.after_response(entry)
