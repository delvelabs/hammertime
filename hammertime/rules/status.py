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
import uuid
from urllib.parse import urljoin, urlparse

from ..ruleset import RejectRequest, Heuristics
from ..http import Entry
from difflib import SequenceMatcher
import simhash
import os
from collections import defaultdict
import re
import random
import string


class RejectStatusCode:

    def __init__(self, *args):
        self.reject_set = set()
        for r in args:
            self.reject_set |= set(r)

    async def after_headers(self, entry):
        if entry.response.code in self.reject_set:
            raise RejectRequest("Status code reject: %s" % entry.response.code)


class DetectSoft404:

    def __init__(self):
        self.engine = None
        self.random_token = str(uuid.uuid4())
        self.child_heuristics = Heuristics()
        self.performed = defaultdict(dict)
        self.soft_404_responses = defaultdict(list)

    def set_engine(self, engine):
        self.engine = engine

    def set_kb(self, kb):
        kb.soft_404_responses = self.soft_404_responses

    async def after_response(self, entry):
        server_address = urljoin(entry.request.url, "/")
        request_url_pattern = self._extract_pattern_from_url(entry.request.url)
        if server_address not in self.performed or request_url_pattern not in self.performed[server_address]:
            # Temporarily assign a future to make sure work is not done twice
            self.performed[server_address][request_url_pattern] = asyncio.Future()
            response = await self._collect_sample(entry, request_url_pattern)
            self.soft_404_responses[server_address].append(response)
            self.performed[server_address][request_url_pattern].set_result(True)
            # Remove the wait lock
            self.performed[server_address][request_url_pattern] = None
        elif self.performed[server_address][request_url_pattern] is not None:
            await self.performed[server_address][request_url_pattern]

        if entry.request.url == server_address:
            return

        if len(entry.response.content) == 0:
            raise RejectRequest("Request is a soft 404.")

        for result in self.soft_404_responses[server_address]:
            if result["pattern"] == request_url_pattern:
                if result["code"] == entry.response.code and self._content_match(entry.response.content,
                                                                                 result["content"]):
                    raise RejectRequest("Request is a soft 404.")

    async def _collect_sample(self, entry, url_pattern):
        url = self._create_random_url_for_url(entry.request.url, url_pattern)
        request = Entry.create(url)
        result = await self.engine.perform_high_priority(request, self.child_heuristics)
        return {"pattern": url_pattern, "code": result.response.code, "content": result.response.content}

    def _content_match(self, response_content, soft_404_content):
        #return simhash.num_differing_bits(self.compute(response_content), self.compute(soft_404_content)) < 3
        matcher = SequenceMatcher(a=response_content, b=soft_404_content, autojunk=False)
        return matcher.ratio() > 0.8

    def compute(self, text):
        tokens = []
        chunk_size = 20
        for i in range(0, len(text), chunk_size):
            tokens.append(text[i:i + chunk_size])
        shingles = [''.join(shingle) for shingle in simhash.shingle(tokens, 4)]
        hashes = [simhash.unsigned_hash(s.encode('utf8')) for s in shingles]
        return simhash.compute(hashes)

    def _extract_pattern_from_url(self, url):
        path = urlparse(url).path
        directory_pattern = self._extract_directory_pattern(path)
        filename_pattern = self._extract_filename_pattern_from_url_path(path)
        return directory_pattern + filename_pattern

    def _extract_directory_pattern(self, url_path):
        directory_path, filename = os.path.split(url_path)
        if directory_path == "/":
            return "/"
        directories = re.split("/", directory_path[1:])  # Skip the leading "/"
        directory_pattern = self._create_pattern_from_string(directories[0])  # only use the pattern of the first directory.
        return "/%s/" % directory_pattern

    def _extract_filename_pattern_from_url_path(self, path):
        directory_path, filename = os.path.split(path)
        if len(filename) > 0:
            filename, extension = os.path.splitext(filename)
            return self._create_pattern_from_string(filename) + extension
        else:
            return ""

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

    def _create_random_url_for_url(self, url, url_pattern):
        path = url_pattern.replace("\d", "".join([random.choice(string.digits) for i in range(random.randint(4, 8))]))
        path = path.replace("\l", "".join([random.choice(string.ascii_lowercase) for i in range(random.randint(4, 8))]))
        path = path.replace("\L", "".join([random.choice(string.ascii_uppercase) for i in range(random.randint(4, 8))]))
        path = path.replace("\i", "".join([random.choice(string.ascii_letters) for i in range(random.randint(4, 8))]))
        path = path.replace("\w", "".join([random.choice(string.ascii_letters + string.digits + "_") for i in range(random.randint(2, 10))]))
        return urljoin(url, path)

    def _is_directory(self, path):
        return len(os.path.split(path)[1]) == 0
