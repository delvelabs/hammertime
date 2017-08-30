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
from unittest.mock import MagicMock, patch, ANY
from fixtures import async_test

from hammertime.engine.aiohttp import AioHttpEngine
from hammertime.http import Entry
from hammertime.ruleset import Heuristics

from aiohttp.test_utils import make_mocked_coro
import asyncio


class TestAioHttpEngine(TestCase):

    @async_test()
    async def test_perform_use_proxy_for_request(self, loop):
        asyncio.set_event_loop(loop)
        engine = AioHttpEngine(loop=loop, proxy="http://some.proxy.com/")
        engine.session.request = make_mocked_coro(return_value=FakeResponse())
        entry = Entry.create("http://www.example.com/1")

        await engine.perform(entry, Heuristics())

        engine.session.request.assert_called_once_with(method=entry.request.method, url="http://www.example.com/1",
                                                       timeout=0.2, proxy="http://some.proxy.com/")

    @async_test()
    async def test_set_proxy(self, loop):
        engine = AioHttpEngine(loop=loop)
        proxy_address = "http://some.proxy.com"

        engine.set_proxy(proxy_address)

        self.assertEqual(engine.proxy, proxy_address)

    def test_constructor_create_client_session_with_connector_with_specified_verify_ssl_value(self):
        engine_verify_ssl = AioHttpEngine(loop=None, verify_ssl=True)
        engine_dont_verify_ssl = AioHttpEngine(loop=None, verify_ssl=False)

        self.assertTrue(engine_verify_ssl.session.connector.verify_ssl)
        self.assertFalse(engine_dont_verify_ssl.session.connector.verify_ssl)

    def test_constructor_load_certification_authority_certificate_in_session_ssl_context(self):
        with patch("ssl.SSLContext.load_verify_locations", MagicMock()):
            engine = AioHttpEngine(loop=None, ca_certificate_file="certificate.cer")

            load_verify_locations = engine.session.connector.ssl_context.load_verify_locations
            load_verify_locations.assert_called_once_with(cafile="certificate.cer")

    @async_test()
    async def test_perform_use_timeout_of_entry_if_not_none(self, loop):
        asyncio.set_event_loop(loop)
        engine = AioHttpEngine(loop=loop, proxy="http://some.proxy.com/")
        engine.session.request = make_mocked_coro(return_value=FakeResponse())
        entry = Entry.create("http://www.example.com/1", arguments={"timeout": 10})

        await engine.perform(entry, Heuristics())

        engine.session.request.assert_called_once_with(method=entry.request.method, url="http://www.example.com/1",
                                                       timeout=10, proxy="http://some.proxy.com/")

    @async_test()
    async def test_specify_header(self, loop):
        asyncio.set_event_loop(loop)
        engine = AioHttpEngine(loop=loop)
        engine.session.request = make_mocked_coro(return_value=FakeResponse())
        entry = Entry.create("http://www.example.com/1", headers={"User-Agent": "Hammertime 1.2.3"})

        await engine.perform(entry, Heuristics())

        engine.session.request.assert_called_once_with(method=entry.request.method, url="http://www.example.com/1",
                                                       timeout=ANY,
                                                       headers={"User-Agent": "Hammertime 1.2.3"})


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
