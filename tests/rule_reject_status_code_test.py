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
from unittest.mock import MagicMock, call, patch
from urllib.parse import urljoin, urlparse

from fixtures import async_test

from hammertime.rules import RejectStatusCode, DetectSoft404
from hammertime.http import Entry, StaticResponse
from hammertime.ruleset import RejectRequest
from hammertime.engine import Engine
from hammertime.kb import KnowledgeBase
import re
import uuid
import random


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
        self.patterns = ["/\l/\d.html", "/\d-\l.js", "/\L/", "/\i", "/.\l.js"]

    @async_test()
    async def test_calls_made_to_random_url_matching_target_url_pattern(self):
        self.rule._create_random_url_for_url = MagicMock(return_value="http://example.com/random.html")

        await self.rule.after_response(self.create_entry("http://example.com/test.html", response_code=400))

        self.engine.mock.perform_high_priority.assert_has_calls([
            call(Entry.create("http://example.com/random.html"), self.rule.child_heuristics)],
            any_order=True)

    @async_test()
    async def test_call_made_to_alternate_url_for_request_url_pattern(self):
        response = StaticResponse(200, {}, content="content")
        self.engine.mock.perform_high_priority.side_effect = lambda entry, heuristics: entry._replace(response=response)
        module_path = "hammertime.rules.status.string"
        with patch(module_path + ".ascii_uppercase", "A"), patch(module_path + ".ascii_lowercase", "a"), \
             patch(module_path + ".digits", "1"), patch("hammertime.rules.status.random.randint", MagicMock(return_value=1)):

            await self.rule.after_response(self.create_entry("http://example.com/test"))
            await self.rule.after_response(self.create_entry("http://example.com/test/"))
            await self.rule.after_response(self.create_entry("http://example.com/.test"))
            await self.rule.after_response(self.create_entry("http://example.com/123/test.html"))
            await self.rule.after_response(self.create_entry("http://example.com/TEST/123.min.js"))
            await self.rule.after_response(self.create_entry("http://example.com/test/TEST.json"))
            await self.rule.after_response(self.create_entry("http://example.com/123/test.png"))
            await self.rule.after_response(self.create_entry("http://example.com/TEST/test.gif"))

            self.engine.mock.perform_high_priority.assert_has_calls([
                call(Entry.create("http://example.com/a"), self.rule.child_heuristics),
                call(Entry.create("http://example.com/a/"), self.rule.child_heuristics),
                call(Entry.create("http://example.com/.a"), self.rule.child_heuristics),
                call(Entry.create("http://example.com/1/a.html"), self.rule.child_heuristics),
                call(Entry.create("http://example.com/A/1.a.js"), self.rule.child_heuristics),
                call(Entry.create("http://example.com/a/A.json"), self.rule.child_heuristics),
                call(Entry.create("http://example.com/1/a.png"), self.rule.child_heuristics),
                call(Entry.create("http://example.com/A/a.gif"), self.rule.child_heuristics),
            ])

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
        await self.rule.after_response(self.create_entry("http://example.com/123/", response_content="response"))
        await self.rule.after_response(self.create_entry("http://example.com/.test", response_content="response"))
        await self.rule.after_response(self.create_entry("http://example.com/123/test.js", response_content="response"))

        self.assertEqual(self.kb.soft_404_responses["http://example.com/"],
                         [{"pattern": "/\l", "code": 200, "content": "response content"},
                          {"pattern": "/\d/", "code": 200, "content": "response content"},
                          {"pattern": "/.\l", "code": 200, "content": "response content"},
                          {"pattern": "/\d/\l.js", "code": 200, "content": "response content"}])

    @async_test()
    async def test_reject_request_with_pattern_and_response_matching_knowledge_base(self):
        for pattern in self.patterns:
            self.kb.soft_404_responses["http://example.com/"].append({"pattern": pattern, "code": 200,
                                                                      "content": "response content"})
            self.rule.performed["http://example.com/"] = {pattern: None}

        urls = [urljoin("http://example.com/", path) for path in ["/test/123.html", "/123-test.js", "/TEST/", "/TesT",
                                                                  "/.test.js"]]
        for url in urls:
            with self.assertRaises(RejectRequest):
                await self.rule.after_response(self.create_entry(url))

    @async_test()
    async def test_dont_reject_request_if_pattern_and_response_not_in_knowledge_base(self):
        for pattern in self.patterns:
            self.kb.soft_404_responses["http://example.com/"].append({"pattern": pattern, "code": 200,
                                                                      "content": "response content"})
            self.rule.performed["http://example.com/"] = {pattern: None}

        try:
            await self.rule.after_response(self.create_entry("http://example.com/test.html", response_content="test"))
            await self.rule.after_response(self.create_entry("http://example.com/test", response_content="test"))
            await self.rule.after_response(self.create_entry("http://example.com/.test", response_content="test"))
            await self.rule.after_response(self.create_entry("http://example.com/test.php", response_content="test"))
        except RejectRequest:
            self.fail("Request rejected.")

    @async_test()
    async def test_homepage_do_not_count_as_soft_404(self):
        for pattern in self.patterns:
            self.kb.soft_404_responses["http://example.com/"].append({"pattern": pattern, "code": 200,
                                                                      "content": "home page"})
            self.rule.performed["http://example.com/"] = {pattern: None}
        try:
            await self.rule.after_response(self.create_entry("http://example.com/", response_content="home page"))
        except RejectRequest:
            self.fail("Request rejected.")

    def test_extract_pattern_from_url(self):
        paths = ["/test", "/test/", "/test.html", "/test.png", "/test.json",
                 "/test/test2/test.123.js", "/test/.test", "/.test", "/", "/.test/123.php", "/TEST/.123.html"]

        patterns = ["/\l", "/\l/", "/\l.html", "/\l.png", "/\l.json", "/\l/\l.\d.js", "/\l/.\l", "/.\l", "/",
                    "/.\l/\d.php", "/\L/.\d.html"]
        url = "http://www.example.com/"
        for path, pattern in zip(paths, patterns):
            self.assertEqual(self.rule._extract_pattern_from_url(urljoin(url, path)), pattern)

    def test_extract_filename_pattern_from_url_path(self):
        paths = ["/test", "/test-123", "/123-test", "/te12st34", "/TEST.html", "/test-123.html", "/123_test.html",
                 "/te12.st34.html", "/.Test", "/.teSt-123", "/.123-test", "/.123_test", "/.te12st34", "/tESt/",
                 "/123/test.js", "/test.php"]
        patterns = ["\l", "\l-\d", "\d-\l", "\w", "\L.html", "\l-\d.html", "\w.html", "\w.\w.html", ".\i",
                    ".\i-\d", ".\d-\l", ".\w", ".\w", "", "\l.js", "\l.php"]
        for path, pattern in zip(paths, patterns):
            self.assertEqual(self.rule._extract_filename_pattern_from_url_path(path), pattern)

    def test_create_random_url_matching_url_pattern_of_request(self):
        self.rule.random_token = str(uuid.uuid4())
        paths = ["/test", "/test-123", "/123-TEST", "/te12st34", "/teST.html", "/test-123.html", "/123_test.html",
                 "/te12.ST34.html", "/.test", "/.test-123", "/.123-test", "/.123_test", "/.te12st34",
                 "/test/", "/test-123/", "/123-test/", "/test/123.json", "/123/test.json"]
        base_url = "http://www.example.com/"

        random_urls = []
        for path in paths:
            url = urljoin(base_url, path)
            random_urls.append(self.rule._create_random_url_for_url(url, self.rule._extract_pattern_from_url(url)))

        expected = ["/[a-z]+", "/[a-z]+-\d+", "/\d+-[A-Z]+", "/\w+", "/[a-zA-Z]+.html", "/[a-z]+-\d+.html",
                    "/\w+.html", "/\w+\.\w+.html", "/.[a-z]+", "/.[a-z]+-\d+", "/.\d+-[a-zA⁻Z]+", "/.\w+", "/.\w+",
                    "/[a-zA-Z]+/", "/[a-zA-Z]+-\d+/", "/\d+-[a-zA-Z]+/", "/[a-z]+/\d+.json", "/\d+/[a-zA-Z]+.json"]
        for result, regex in zip(random_urls, expected):
            self.assertTrue(result.startswith(base_url))
            try:
                self.assertIsNotNone(re.match(regex, urlparse(result).path))
            except Exception as e:
                print(result)
                print(regex)
                raise e

    def test_extract_directory_pattern_from_url_path(self):
        paths = ["/test/", "/123/", "/TEST/", "/teST/", "/test123/", "/.test/", "/.123/", "/123-test/", "/.TEST-123/",
                 "/", "/test.html"]
        filenames = ["test.json", "test.html", "test.js", "", "test", ".test", "test.123.php"]
        url_path = [path + random.choice(filenames) for path in paths]

        directory_patterns = [self.rule._extract_directory_pattern(path) for path in url_path]

        expected = ["/\l/", "/\d/", "/\L/", "/\i/", "/\w/", "/.\l/", "/.\d/", "/\d-\l/", "/.\L-\d/", "/", "/"]
        self.assertEqual(directory_patterns, expected)

    def test_extract_directory_pattern_from_url_path_return_pattern_of_first_directory(self):
        paths = ["/test/123/", "/123/test/", "/TEST/test/", "/teST/123/", "/.test/123/", "/.123/test/", "/123-test/12/",
                 "/123/test-123/"]
        filenames = ["test.json", "test.html", "test.js", "", "test", ".test", "test.123.php"]
        url_path = [path + random.choice(filenames) for path in paths]

        directory_patterns = [self.rule._extract_directory_pattern(path) for path in url_path]

        expected = ["/\l/", "/\d/", "/\L/", "/\i/", "/.\l/", "/.\d/", "/\d-\l/", "/\d/"]
        self.assertEqual(directory_patterns, expected)

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
