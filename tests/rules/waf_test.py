# hammertime: A high-volume http fetch library
# Copyright (C) 2018-  Delve Labs inc.
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

from fixtures import async_test
from hammertime.rules.waf import RejectWebApplicationFirewall
from hammertime.http import Entry, StaticResponse
from hammertime.ruleset import RejectRequest


class RejectWebApplicationFirewallTest(TestCase):

    def setUp(self):
        self.rule = RejectWebApplicationFirewall()

    @async_test()
    async def test_simple_request(self):
        entry = Entry.create("http://example.com/test", response=StaticResponse(200, content="Hello world.",
                                                                                headers={}))

        await self.rule.after_response(entry)

        self.assertTrue(entry.response.code, 200)

    @async_test()
    async def test_reject_bigip_asm(self):
        content = "<html><head><title>Request Rejected</title></head><body>The requested URL was rejected. " \
                  "Please consult with your administrator.<br><br>Your support ID is: 18012286000693285704" \
                  "</body></html>"
        entry = Entry.create("http://example.com/test", response=StaticResponse(200, content=content,
                                                                                headers={}))

        with self.assertRaises(RejectRequest):
            await self.rule.after_response(entry)

        self.assertTrue(entry.response.code, 200)
