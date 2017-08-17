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
from unittest.mock import MagicMock, call, ANY

from fixtures import async_test

from hammertime.rules import RejectStatusCode, DetectSoft404
from hammertime.http import Entry, StaticResponse
from hammertime.ruleset import RejectRequest
from hammertime.engine import Engine
from hammertime.kb import KnowledgeBase


class RejectStatusCodeTest(TestCase):

    @async_test()
    async def test_reject_nothing(self):
        r = RejectStatusCode()
        await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(200, {})))
        await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(302, {})))

    @async_test()
    async def test_do_not_reject_outside_specified_ranges(self):
        r = RejectStatusCode(range(400, 410), range(500, 700))
        await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(200, {})))
        await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(302, {})))
        await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(410, {})))
        await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(460, {})))

    @async_test()
    async def test_do_not_reject_reject_within_the_specified_ranges(self):
        r = RejectStatusCode(range(400, 410), range(500, 700))
        with self.assertRaises(RejectRequest):
            await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(400, {})))

        with self.assertRaises(RejectRequest):
            await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(409, {})))

        with self.assertRaises(RejectRequest):
            await r.after_headers(Entry.create("http://example.om/test", response=StaticResponse(503, {})))


class DetectSoft404Test(TestCase):

    def setUp(self):
        self.rule = DetectSoft404()
        self.rule.random_token = "not-so-random"
        self.engine = FakeEngine()
        self.rule.set_engine(self.engine)
        self.kb = KnowledgeBase()
        self.rule.set_kb(self.kb)

    @async_test()
    async def test_calls_made_to_alternate_urls(self):
        await self.rule.after_response(self.create_entry("http://example.com/test", response_code=400))

        self.engine.mock.perform_high_priority.assert_has_calls([
            call(Entry.create("http://example.com/not-so-random.aspx", arguments=ANY), self.rule.child_heuristics),
            call(Entry.create("http://example.com/not-so-random.html", arguments=ANY), self.rule.child_heuristics),
        ], any_order=True)

    @async_test()
    async def test_calls_not_made_second_time_around(self):
        await self.rule.after_response(self.create_entry("http://example.com/test", response_code=400))

        self.engine.mock.reset_mock()

        await self.rule.after_response(self.create_entry("http://example.com/test", response_code=400))

        self.engine.mock.perform_high_priority.assert_not_called()

    @async_test()
    async def test_add_alternate_url_response_to_knowledge_base(self):
        response = StaticResponse(200, {})
        response.content = "response content"
        self.engine.mock.perform_high_priority = lambda entry, heuristics: entry._replace(response=response)

        await self.rule.after_response(self.create_entry("http://example.com/test", response_content="response"))

        self.assertEqual(self.kb.soft_404_responses["http://example.com/"],
                         [{"pattern": pattern, "code": 200, "content": "response content"} for pattern in
                          self.rule.patterns])

    @async_test()
    async def test_reject_request_with_pattern_and_response_matching_knowledge_base(self):
        self.kb.soft_404_responses["http://example.com/"] = \
            [{"pattern": pattern, "code": 200, "content": "response content"} for pattern in self.rule.patterns]
        self.rule.performed["http://example.com/"] = None

        for pattern in self.rule.patterns:
            url = "http://example.com%s" % (pattern % "test")
            with self.assertRaises(RejectRequest):
                await self.rule.after_response(self.create_entry(url))

    @async_test()
    async def test_reject_request_if_pattern_not_listed_but_response_matching_any_soft_404_response(self):
        self.kb.soft_404_responses["http://example.com/"] = [{"pattern": "/%s.html", "code": 200,
                                                              "content": "response content"}]
        self.rule.performed["http://example.com/"] = None

        with self.assertRaises(RejectRequest):
            await self.rule.after_response(self.create_entry("http://example.com/test.some-random-file-extension"))

    @async_test()
    async def test_dont_reject_request_if_pattern_and_response_not_in_knowledge_base(self):
        self.kb.soft_404_responses["http://example.com/"] = \
            [{"pattern": pattern, "code": 200, "content": "response content"} for pattern in self.rule.patterns]
        self.rule.performed["http://example.com/"] = None

        try:
            await self.rule.after_response(self.create_entry("http://example.com/test.html", response_content="test"))
            await self.rule.after_response(self.create_entry("http://example.com/test", response_content="test"))
            await self.rule.after_response(self.create_entry("http://example.com/.test", response_content="test"))
            await self.rule.after_response(self.create_entry("http://example.com/test.php", response_content="test"))
        except RejectRequest:
            self.fail("Request rejected.")

    @async_test()
    async def test_empty_response_count_as_soft_404(self):
        with self.assertRaises(RejectRequest):
            await self.rule.after_response(self.create_entry("http://example.com/test.html", response_content=""))

    @async_test()
    async def test_homepage_do_not_count_as_soft_404(self):
        self.kb.soft_404_responses["http://example.com/"] = \
            [{"pattern": pattern, "code": 200, "content": "home page"} for pattern in self.rule.patterns]
        self.rule.performed["http://example.com/"] = None
        try:
            await self.rule.after_response(self.create_entry("http://example.com/", response_content="home page"))
        except RejectRequest:
            self.fail("Request rejected.")

    def create_entry(self, url, response_code=200, response_content="response content"):
        response = StaticResponse(response_code, {}, response_content)
        return Entry.create(url, response=response)


class FakeEngine(Engine):

    def __init__(self):
        self.mock = MagicMock()

    async def perform(self, entry, heuristics):
        return self.mock.perform(entry, heuristics)

    async def perform_high_priority(self, entry, heuristics):
        return self.mock.perform_high_priority(entry, heuristics)
