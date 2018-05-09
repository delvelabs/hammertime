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

import asyncio
from urllib.parse import urljoin, urlparse
import os
from collections import defaultdict
from difflib import SequenceMatcher
import re
import random
import string
import hashlib

from ..ruleset import RejectRequest, StopRequest
from ..http import Entry
from .simhash import Simhash, DEFAULT_FILTER


class RejectStatusCode:

    def __init__(self, *args):
        self.reject_set = set()
        for r in args:
            self.reject_set |= set(r)

    async def after_headers(self, entry):
        if entry.response.code in self.reject_set:
            raise RejectRequest("Status code reject: %s" % entry.response.code)


class DetectSoft404:

    def __init__(self, distance_threshold=5, match_filter=DEFAULT_FILTER, token_size=4, sample_length=5120):
        self.engine = None
        self.performed = defaultdict(dict)
        self.soft_404_responses = defaultdict(dict)
        self.distance_threshold = distance_threshold
        self.match_filter = match_filter
        self.token_size = token_size
        self.sample_length = sample_length

    def set_engine(self, engine):
        self.engine = engine

    def set_kb(self, kb):
        kb.soft_404_responses = self.soft_404_responses

    def load_kb(self, kb):
        self.soft_404_responses = kb.soft_404_responses

    def set_child_heuristics(self, heuristics):
        self.child_heuristics = heuristics

    async def on_request_successful(self, entry):
        if entry.response.code != 200:
            entry.result.soft404 = False
        else:
            soft_404_response = await self.get_soft_404_sample(entry.request.url)
            if soft_404_response is not None and self._match(entry.response, soft_404_response):
                entry.result.soft404 = True
            else:
                entry.result.soft404 = False

    async def get_soft_404_sample(self, url):
        server_address = urljoin(url, "/")
        if url == server_address:  # skip home page.
            return None
        request_url_pattern = self._extract_pattern_from_url(url)
        if request_url_pattern not in self.performed[server_address]:
            try:
                # Temporarily assign a future to make sure work is not done twice
                self.performed[server_address][request_url_pattern] = asyncio.Future()
                response = await self._collect_sample(url, request_url_pattern)
                self.soft_404_responses[server_address][request_url_pattern] = response
            except (StopRequest, RejectRequest):
                self.soft_404_responses[server_address][request_url_pattern] = None
            finally:
                # Remove the wait lock
                self.performed[server_address][request_url_pattern].set_result(True)
                self.performed[server_address][request_url_pattern] = None
        elif self.performed[server_address][request_url_pattern] is not None:
            await self.performed[server_address][request_url_pattern]
        return self.soft_404_responses[server_address][request_url_pattern]

    async def _collect_sample(self, url, url_pattern):
        url = self._create_random_url(url, url_pattern)
        request = Entry.create(url)
        result = await self.engine.perform_high_priority(request, self.child_heuristics)
        try:
            simhash = self._simhash(result.response)
            return {"code": result.response.code,
                    "content_simhash": simhash,
                    "raw_content_hash": self._hash(result.response),
                    "content_sample": self._sample(result.response)}
        except UnicodeDecodeError:  # Response content is not text, store the hash of the raw data:
            return {"code": result.response.code,
                    "raw_content_hash": self._hash(result.response),
                    "content_sample": self._sample(result.response)}

    def _match(self, response, soft_404_response):
        if soft_404_response["code"] == response.code:
            if "raw_content_hash" in soft_404_response:
                if self._hash(response) == soft_404_response["raw_content_hash"]:
                    return True

            if "content_simhash" in soft_404_response:
                try:
                    resp_hash = Simhash(self._simhash(response))
                    distance = resp_hash.distance(Simhash(soft_404_response["content_simhash"]))
                    if distance < self.distance_threshold:
                        return True
                except UnicodeDecodeError:  # response content is not text, cannot match text.
                    pass

            if self.sample_length and "content_sample" in soft_404_response:
                sample = self._sample(response)
                matcher = SequenceMatcher(isjunk=None, a=soft_404_response["content_sample"], b=sample, autojunk=False)

                # This content is almost similar to a generated 404, therefore it's a 404.
                if matcher.ratio() > 0.8:
                    return True

        return False

    def _hash(self, response):
        return hashlib.md5(response.raw).digest()

    def _simhash(self, response):
        return Simhash(response.content, filter=self.match_filter, token_size=self.token_size).value

    def _sample(self, response):
        return response.raw[0:self.sample_length]

    def _extract_pattern_from_url(self, url):
        """Return the path part of the URL with the last element replaced with its pattern in a regex-like format:
        \l -> lowercase letters, same as [a-z]+
        \L -> uppercase letters, same as [A-Z]+
        \i -> letters ignoring case, same as [a-zA-Z]+
        \d -> digits, same as \d+
        \w -> word characters (letters, digits, underscores), same as \w+
        All other characters match themselves
        """
        path = urlparse(url).path
        directories, filename = os.path.split(path)
        if len(filename) > 0:
            pattern = self._get_pattern_for_filename(filename)
            if directories[-1] != "/":
                directories += "/"
            return directories + pattern
        else:
            return self._get_pattern_for_directory(directories)

    def _get_pattern_for_directory(self, directory_path):
        if directory_path == "/":
            return "/"
        directory_path = directory_path.strip("/")
        directories = directory_path.split("/")
        if len(directories) > 1:
            directory_pattern = self._create_pattern_from_string(directories[-1])
            return "/%s/%s/" % ("/".join(directories[:-1]), directory_pattern)
        else:
            return "/%s/" % self._create_pattern_from_string(directories[0])

    def _get_pattern_for_filename(self, filename):
        filename, extension = os.path.splitext(filename)
        return self._create_pattern_from_string(filename) + extension

    def _create_pattern_from_string(self, string):
        parts = re.split("\W", string)
        pattern = re.sub("\w+", "{}", string)
        pattern_list = []
        for part in parts:
            if len(part) > 0:
                if re.fullmatch("[a-z]+", part):
                    pattern_list.append("\l")
                elif re.fullmatch("[A-Z]+", part):
                    pattern_list.append("\L")
                elif re.fullmatch("[a-zA-Z]+", part):
                    pattern_list.append("\i")
                elif re.fullmatch("\d+", part):
                    pattern_list.append("\d")
                else:
                    pattern_list.append("\w")
        return pattern.format(*pattern_list)

    def _create_random_url(self, url, path):
        replace_patterns = ["\l", "\L", "\i", "\d", "\w"]
        for pattern in replace_patterns:
            path = path.replace(pattern, self._create_random_string(pattern, random.randint(8, 15)))
        return urljoin(url, path)

    def _create_random_string(self, pattern, length):
        choices = None
        if pattern == "\l":
            choices = string.ascii_lowercase
        elif pattern == "\L":
            choices = string.ascii_uppercase
        elif pattern == "\i":
            choices = string.ascii_letters
        elif pattern == "\w":
            choices = string.ascii_letters + string.digits + "_"
        elif pattern == "\d":
            choices = string.digits
        if choices is not None:
            return "".join([random.choice(choices) for _ in range(length)])
        else:
            return ""


class RejectSoft404:

    async def on_request_successful(self, entry):
        if entry.result.soft404:
            raise RejectRequest("Response to %s is a soft 404." % entry.request)
