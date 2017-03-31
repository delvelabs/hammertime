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
from unittest.mock import MagicMock
from fixtures import async_test

from hammertime.engine.aiohttp import AioHttpEngine
from hammertime.http import Entry
from hammertime.ruleset import Heuristics

from aiohttp.test_utils import make_mocked_coro
import asyncio


class TestAioHttpEngine(TestCase):

    @async_test()
    async def test_perform_use_proxy_of_http_request(self, loop):
        engine = AioHttpEngine(loop=loop)
        engine.session.request = make_mocked_coro(return_value=FakeResponse())
        entry = Entry.create("http://www.example.com/1", proxy="http://some.proxy.com/")
        asyncio.set_event_loop(loop)

        await engine.perform(entry, Heuristics())

        engine.session.request.assert_called_once_with(method=entry.request.method, url="http://www.example.com/1",
                                                       timeout=0.2, proxy="http://some.proxy.com/")


class FakeResponse:

    def __init__(self):
        self.content = MagicMock()
        self.content.read = make_mocked_coro()
        self.status = 200
        self.headers = MagicMock()

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
