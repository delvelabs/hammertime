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

from hammertime.engine.aiohttp import AioHttpEngine, Response
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
                                                       timeout=0.2, proxy="http://some.proxy.com/",
                                                       allow_redirects=False, ssl=None)

    @async_test()
    async def test_set_proxy(self, loop):
        engine = AioHttpEngine(loop=loop)
        proxy_address = "http://some.proxy.com"

        engine.set_proxy(proxy_address)

        self.assertEqual(engine.proxy, proxy_address)

    @async_test()
    async def test_default_ssl_parameters(self, loop):
        engine = AioHttpEngine(loop=loop)
        engine.session.request = make_mocked_coro(return_value=FakeResponse())
        entry = Entry.create("http://www.example.com/")

        await engine.perform(entry, Heuristics())

        engine.session.request.assert_called_once_with(method=entry.request.method, url=entry.request.url,
                                                       allow_redirects=False, timeout=0.2, ssl=None)


    @async_test()
    async def test_set_ssl_parameters_set_certification_authority_certificate(self, loop):
        ssl_context = "ssl_context"
        with patch("ssl.create_default_context", MagicMock(return_value=ssl_context)) as create_default_context:
            engine = AioHttpEngine(loop=loop)
            engine.session.request = make_mocked_coro(return_value=FakeResponse())
            entry = Entry.create("http://www.example.com/")

            engine.set_ssl_parameters(ca_certificate_file="certificate.cer")
            await engine.perform(entry, Heuristics())

            engine.session.request.assert_called_once_with(method=entry.request.method, url=entry.request.url,
                                                           allow_redirects=False, timeout=0.2, ssl=ssl_context)
            create_default_context.assert_called_once_with(cafile="certificate.cer")

    @async_test()
    async def test_set_ssl_parameters_dont_verify_ssl(self, loop):
        engine = AioHttpEngine(loop=loop)
        engine.session.request = make_mocked_coro(return_value=FakeResponse())
        entry = Entry.create("http://www.example.com/")

        engine.set_ssl_parameters(verify_ssl=False)
        await engine.perform(entry, Heuristics())

        engine.session.request.assert_called_once_with(method=entry.request.method, url=entry.request.url,
                                                       allow_redirects=False, timeout=0.2, ssl=False)


    @async_test()
    async def test_perform_use_timeout_of_entry_if_not_none(self, loop):
        asyncio.set_event_loop(loop)
        engine = AioHttpEngine(loop=loop, proxy="http://some.proxy.com/")
        engine.session.request = make_mocked_coro(return_value=FakeResponse())
        entry = Entry.create("http://www.example.com/1", arguments={"timeout": 10})

        await engine.perform(entry, Heuristics())

        engine.session.request.assert_called_once_with(method=entry.request.method, url="http://www.example.com/1",
                                                       timeout=10, proxy="http://some.proxy.com/",
                                                       allow_redirects=False, ssl=None)

    @async_test()
    async def test_specify_header(self, loop):
        asyncio.set_event_loop(loop)
        engine = AioHttpEngine(loop=loop)
        engine.session.request = make_mocked_coro(return_value=FakeResponse())
        entry = Entry.create("http://www.example.com/1", headers={"User-Agent": "Hammertime 1.2.3"})

        await engine.perform(entry, Heuristics())

        engine.session.request.assert_called_once_with(method=entry.request.method, url="http://www.example.com/1",
                                                       timeout=ANY, allow_redirects=False,
                                                       headers={"User-Agent": "Hammertime 1.2.3"}, ssl=None)


class TestResponse(TestCase):

    def test_partial_content_return_decoded_truncated_raw_bytes(self):
        raw_bytes = b"abcdefg"
        response = Response(200, {})
        response.set_content(raw_bytes, False)

        self.assertEqual(response.partial_content, "abcdefg")

    def test_partial_content_ignore_truncated_utf8_characters_when_decoding(self):
        raw_bytes = "abcdé".encode("utf-8")[:-1]  # 'é' 2nd byte will be missing
        response = Response(200, {})
        response.set_content(raw_bytes, False)

        self.assertEqual(response.partial_content, "abcd")

    def test_partial_content_raise_unicode_decode_error_if_error_not_caused_by_truncated_content(self):
        raw_bytes = b"\x80" * 10  # Not an encoded utf-8 string
        response = Response(200, {})
        response.set_content(raw_bytes, False)

        with self.assertRaises(UnicodeDecodeError):
            response.partial_content


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
