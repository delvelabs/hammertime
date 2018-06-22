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
from urllib.parse import urljoin, urlparse
import re
import uuid
import hashlib
from aiohttp.test_utils import make_mocked_coro

from fixtures import async_test
from hammertime.rules.status import ContentSignature, SignatureComparator
from hammertime.rules import RejectStatusCode, DetectSoft404
from hammertime.http import Entry, StaticResponse
from hammertime.ruleset import RejectRequest, StopRequest
from hammertime.engine import Engine
from hammertime.kb import KnowledgeBase
from hammertime.rules.simhash import Simhash
from hammertime.engine.aiohttp import Response


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


class TestDetectSoft404(TestCase):

    def setUp(self):
        self.rule = DetectSoft404(collect_retry_delay=0.0)
        self.engine = FakeEngine()
        self.rule.set_engine(self.engine)
        self.kb = KnowledgeBase()
        self.rule.set_kb(self.kb)
        self.rule.child_heuristics = MagicMock()
        self.host = "http://example.com"

    @async_test()
    async def test_call_made_to_alternate_url_for_request_url_pattern(self):
        urls = ["/test", "/test/", "/.test", "/123/test.html", "/TEST/123.min.js", "/test/TEST.json", "/123/test.png",
                "/TEST/test.gif"]
        alternate_urls = ["/a", "/a/", "/.a", "/123/a.html", "/TEST/1.a.js", "/test/A.json", "/123/a.png",
                          "/TEST/a.gif"]
        module_path = "hammertime.rules.status.string"
        response = StaticResponse(200, {}, content="content")
        self.engine.response = response

        with patch(module_path + ".ascii_uppercase", "A"), patch(module_path + ".ascii_lowercase", "a"), \
            patch(module_path + ".digits", "1"), \
                patch("hammertime.rules.status.random.randint", MagicMock(return_value=1)):

            for url, alternate_url in zip(urls, alternate_urls):
                await self.rule.on_request_successful(self.create_entry(self.host + url))
                self.assertRequested(self.host + alternate_url)

    @async_test()
    async def test_calls_not_made_second_time_around(self):
        entry = self.create_entry("http://example.com/test", response_content="response")
        self.engine.mock.perform_high_priority.return_value = entry
        await self.rule.on_request_successful(self.create_entry("http://example.com/test"))

        self.engine.mock.reset_mock()

        await self.rule.on_request_successful(self.create_entry("http://example.com/test"))

        self.engine.mock.perform_high_priority.assert_not_called()

    @async_test()
    async def test_remove_lock_if_stop_request_raised(self):
        self.engine.mock.perform_high_priority.side_effect = StopRequest("Timeout reached.")

        with self.assertRaises(RejectRequest):
            await self.rule.on_request_successful(self.create_entry("http://example.com/test"))

        self.assertEqual(self.rule.performed["http://example.com/"]["/\l"], None)

    @async_test()
    async def test_add_alternate_url_response_to_knowledge_base(self):
        response = StaticResponse(200, {})
        response.content = "response content"
        self.engine.response = response

        await self.rule.on_request_successful(self.create_entry("http://example.com/test",
                                                                response_content="response"))
        await self.rule.on_request_successful(self.create_entry("http://example.com/123/",
                                                                response_content="response"))
        await self.rule.on_request_successful(self.create_entry("http://example.com/.test",
                                                                response_content="response"))
        await self.rule.on_request_successful(self.create_entry("http://example.com/123/test.js",
                                                                response_content="response"))

        simhash = Simhash(response.content).value
        raw = self.rule.signature_comparator._hash(response)
        self.assertEqual(self.kb.soft_404_responses["http://example.com/"], {
            "/\l": ContentSignature(code=200, content_simhash=simhash, content_hash=raw, content_sample=ANY),
            "/\d/": ContentSignature(code=200, content_simhash=simhash, content_hash=raw, content_sample=ANY),
            "/.\l": ContentSignature(code=200, content_simhash=simhash, content_hash=raw, content_sample=ANY),
            "/123/\l.js": ContentSignature(code=200, content_simhash=simhash, content_hash=raw, content_sample=ANY)})

    @async_test()
    async def test_add_None_to_knowledge_base_if_request_failed(self):
        self.engine.mock.perform_high_priority.side_effect = StopRequest("Timeout reached.")

        with self.assertRaises(RejectRequest):
            await self.rule.on_request_successful(self.create_entry("http://example.com/test",
                                                                    response_content="response"))

        self.assertEqual(self.kb.soft_404_responses["http://example.com/"], {"/\l": None})

    @async_test()
    async def test_add_hash_of_raw_content_if_response_content_of_sample_is_not_text(self):
        bytes = b'Invalid UTF8 x\x80Z"'
        sample_response = Response(200, {})
        sample_response.set_content(bytes, True)
        self.engine.response = sample_response

        await self.rule.on_request_successful(self.create_entry("http://example.com/test", response_content="response"))

        self.assertEqual(self.kb.soft_404_responses["http://example.com/"], {
                "/\l": ContentSignature(code=200, content_hash=hashlib.md5(bytes).digest(), content_sample=ANY)})

    @async_test()
    async def test_mark_request_has_soft404_if_pattern_and_response_match_request_in_knowledge_base(self):
        for pattern in ["/test/\d.html", "/\d-\l.js", "/\L/", "/\i", "/abc/.\l.js"]:
            simhash = Simhash("response content").value
            self.kb.soft_404_responses["http://example.com/"][pattern] = ContentSignature(code=200,
                                                                                          content_simhash=simhash)
            self.rule.performed["http://example.com/"][pattern] = None

        urls = [urljoin("http://example.com/", path) for path in ["/test/123.html", "/123-test.js", "/TEST/", "/TesT",
                                                                  "/abc/.test.js"]]
        entries = [self.create_entry(url) for url in urls]
        for entry in entries:
            await self.rule.on_request_successful(entry)

        self.assertTrue(all(entry.result.soft404 for entry in entries))

    @async_test()
    async def test_dont_mark_as_soft404_if_no_match_in_knowledge_base(self):
        simhash = Simhash("response content").value
        for pattern in ["/\l.html", "/\l", "/.\l", "/\l.php"]:
            self.kb.soft_404_responses["http://example.com/"][pattern] = ContentSignature(code=200,
                                                                                          content_simhash=simhash)
            self.rule.performed["http://example.com/"][pattern] = None
        entries = [self.create_entry("http://example.com/test.html", response_content="test"),
                   self.create_entry("http://example.com/test", response_content="test"),
                   self.create_entry("http://example.com/.test", response_content="test"),
                   self.create_entry("http://example.com/test.php", response_content="test")]
        for entry in entries:
            await self.rule.on_request_successful(entry)

        self.assertFalse(any(entry.result.soft404 for entry in entries))

    @async_test()
    async def test_dont_mark_as_soft404_if_response_in_knowledge_base_is_none(self):
        self.kb.soft_404_responses["http://example.com/"]["/\l"] = None
        self.rule.performed["http://example.com/"] = {"/\l": None}
        entry = self.create_entry("http://example.com/test", response_content="test")

        with self.assertRaises(RejectRequest):
            await self.rule.on_request_successful(entry)

        self.assertFalse(entry.result.soft404)

    @async_test()
    async def test_compare_hash_of_raw_content_if_raw_content_hash_in_knowledge_base(self):
        raw = b'Invalid UTF8 x\x80Z"'
        _hash = hashlib.md5(raw).digest()
        self.kb.soft_404_responses["http://example.com/"]["/\l"] = ContentSignature(code=200, content_hash=_hash)
        self.rule.performed["http://example.com/"] = {"/\l": None}
        response = Response(200, {})
        response.set_content(raw, True)
        entry = Entry.create("http://example.com/test", response=response)

        await self.rule.on_request_successful(entry)

        self.assertTrue(entry.result.soft404)

    def test_content_that_is_not_text_never_match_content_simhash_of_sample(self):
        raw = b'Invalid UTF8 x\x80Z"'
        response = Response(200, {})
        response.set_content(raw, True)

        self.assertFalse(self.rule.signature_comparator.match(response,
                                                              ContentSignature(code=200, content_simhash=12345),
                                                              url="http://example.com/"))

    @async_test()
    async def test_homepage_do_not_count_as_soft_404(self):
        simhash = Simhash("response content").value
        for pattern in ["/\l/\d.html", "/\d-\l.js", "/\L/", "/\i", "/.\l.js"]:
            self.kb.soft_404_responses["http://example.com/"][pattern] = {"code": 200, "content_simhash": simhash}
            self.rule.performed["http://example.com/"] = {pattern: None}
        entry = self.create_entry("http://example.com/", response_content="home page")

        await self.rule.on_request_successful(entry)

        self.assertFalse(entry.result.soft404)

    @async_test()
    async def test_on_request_successful(self):
        entry = Entry.create("http://example.com/", response=StaticResponse(404, {}))
        self.rule.get_soft_404_sample = make_mocked_coro()

        await self.rule.on_request_successful(entry)

        self.rule.get_soft_404_sample.assert_not_called()
        self.assertFalse(entry.result.soft404)

    def test_extract_pattern_from_url_replace_last_element_in_path_with_its_pattern(self):
        paths = ["/test", "/test/", "/test.html", "/test.png", "/test.json",
                 "/test/test2/test.123.js", "/test/.test", "/.test", "/", "/.test/123.php", "/TEST/.123.html"]

        patterns = ["/\l", "/\l/", "/\l.html", "/\l.png", "/\l.json", "/test/test2/\l.\d.js", "/test/.\l", "/.\l", "/",
                    "/.test/\d.php", "/TEST/.\d.html"]
        url = "http://www.example.com/"
        for path, pattern in zip(paths, patterns):
            self.assertEqual(self.rule._extract_pattern_from_url(urljoin(url, path)), pattern)

    def test_get_pattern_for_filename(self):
        filenames = ["test", "test-123", "123-test", "te12st34", "TEST.html", "test-123.html", "123_test.html",
                     "te12.st34.html", ".Test", ".teSt-123", ".123-test", ".123_test", ".te12st34", "test.php"]
        patterns = ["\l", "\l-\d", "\d-\l", "\w", "\L.html", "\l-\d.html", "\w.html", "\w.\w.html", ".\i",
                    ".\i-\d", ".\d-\l", ".\w", ".\w", "\l.php"]
        for filename, pattern in zip(filenames, patterns):
            self.assertEqual(self.rule._get_pattern_for_filename(filename), pattern)

    def test_get_pattern_for_directory(self):
        directories = ["/test", "/123", "/TEST", "/teST", "/test123", "/.test", "/.123", "/123-test",
                       "/.TEST-123", "/"]

        directory_patterns = [self.rule._get_pattern_for_directory(dir) for dir in directories]

        expected = ["/\l/", "/\d/", "/\L/", "/\i/", "/\w/", "/.\l/", "/.\d/", "/\d-\l/", "/.\L-\d/", "/"]
        self.assertEqual(directory_patterns, expected)

    def test_get_pattern_for_directory_replace_only_last_subdirectory_of_path_with_its_pattern(self):
        paths = ["/test/123", "/123/test", "/test/TEST", "/123/teST", "/123/.test", "/test/.123", "/dir/123-test",
                 "/123/test-123"]

        directory_patterns = [self.rule._get_pattern_for_directory(path) for path in paths]

        expected = ["/test/\d/", "/123/\l/", "/test/\L/", "/123/\i/", "/123/.\l/", "/test/.\d/", "/dir/\d-\l/",
                    "/123/\l-\d/"]
        self.assertEqual(directory_patterns, expected)

    def test_create_random_url_matching_url_pattern_of_request(self):
        self.rule.random_token = str(uuid.uuid4())
        paths = ["/test", "/test-123", "/123-TEST", "/te12st34", "/teST.html", "/test-123.html", "/123_test.html",
                 "/te12.ST34.html", "/.test", "/.test-123", "/.123-test", "/.123_test", "/.te12st34",
                 "/test/", "/test-123/", "/123-test/", "/test/123.json", "/123/test.json"]
        base_url = "http://www.example.com/"

        random_urls = []
        for path in paths:
            url = urljoin(base_url, path)
            random_urls.append(self.rule._create_random_url(url, self.rule._extract_pattern_from_url(url)))

        expected = ["/[a-z]+", "/[a-z]+-\d+", "/\d+-[A-Z]+", "/\w+", "/[a-zA-Z]+.html", "/[a-z]+-\d+.html",
                    "/\w+.html", "/\w+\.\w+.html", "/.[a-z]+", "/.[a-z]+-\d+", "/.\d+-[a-zA⁻Z]+", "/.\w+", "/.\w+",
                    "/[a-zA-Z]+/", "/[a-zA-Z]+-\d+/", "/\d+-[a-zA-Z]+/", "/[a-z]+/\d+.json", "/\d+/[a-zA-Z]+.json"]
        for result, regex in zip(random_urls, expected):
            self.assertTrue(result.startswith(base_url))
            self.assertIsNotNone(re.match(regex, urlparse(result).path))

    def test_obtain_potentially_valid_parent_paths(self):
        self.assertIn("http://example.com/admin/",
                      list(self.rule.enumerate_candidates("http://example.com/admin/file.txt")))
        self.assertIn("http://example.com/admin/much/",
                      list(self.rule.enumerate_candidates("http://example.com/admin/much/longer/path")))
        self.assertIn("http://example.com/admin/much",
                      list(self.rule.enumerate_candidates("http://example.com/admin/much/longer/path")))

    def create_entry(self, url, response_code=200, response_content="response content"):
        response = StaticResponse(response_code, {}, response_content)
        return Entry.create(url, response=response)

    def assertRequested(self, url):
        entry = self.engine.mock.perform_high_priority.call_args[0][0]
        self.assertEqual(entry.request.url, url)
        self.engine.mock.reset_mock()


class SignatureComparatorTest(TestCase):

    def test_sampling_removes_origin_information(self):
        sample_a = '<iframe sandbox="allow-same-origin allow-scripts allow-top-navigation" id="preferredMethod" src="https://www.example.com:2096/unprotected/loader.html?random=Hh2c1OlZNtIkWS8F&amp;goto_uri=%2ffiles.inc" style="display:none;"></iframe>' * 10 # noqa
        sample_b = '<iframe sandbox="allow-same-origin allow-scripts allow-top-navigation" id="preferredMethod" src="https://www.example.com:2096/unprotected/loader.html?random=nsfufafuidafKNUF&amp;goto_uri=%2fabc12345678901234567890.inc" style="display:none;"></iframe>' * 10 # noqa

        comparator = SignatureComparator()
        sig_a = ContentSignature(code=200, content_sample=comparator._sample(sample_a, "http://example.com/files.inc"))
        sig_b = ContentSignature(code=200, content_sample=comparator._sample(sample_b, "http://example.com/abc123.inc"))
        self.assertTrue(sig_a.match_sample(sig_b))


class FakeEngine(Engine):

    def __init__(self):
        self.mock = MagicMock()
        self.response = None

    async def perform(self, entry, heuristics):
        return self.mock.perform(entry, heuristics)

    async def perform_high_priority(self, entry, heuristics):
        entry.response = self.response or StaticResponse(200, {}, content="content")
        self.mock.perform_high_priority(entry, heuristics)
        return entry
