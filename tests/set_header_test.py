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

import unittest
from fixtures import async_test

from hammertime.http import Entry
from hammertime.rules.header import SetHeader


class SetHeaderTest(unittest.TestCase):

    @async_test()
    async def test_set_header(self):
        rule = SetHeader("User-Agent", "HammerTime 1.2")
        entry = Entry.create("http://example.com")
        await rule.before_request(entry)

        self.assertEqual("HammerTime 1.2", entry.request.headers["User-Agent"])
