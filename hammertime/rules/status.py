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

    def __init__(self, *args, exception_class=RejectRequest):
        self.exception_class = exception_class
        self.reject_set = set()
        for r in args:
            self.reject_set |= set(r)

    async def after_headers(self, entry):
        if entry.response.code in self.reject_set:
            raise self.exception_class("Status code reject: %s" % entry.response.code)


class DetectSoft404:

    def __init__(self, distance_threshold=5, match_filter=DEFAULT_FILTER, token_size=4, sample_length=5120,
                 collect_retry_delay=5.0, confirmation_factor=1):
        self.engine = None
        self.performed = defaultdict(dict)
        self.confirmation_factor = confirmation_factor
        self.soft_404_responses = defaultdict(dict)
        self.collect_retry_delay = collect_retry_delay
        self.signature_comparator = SignatureComparator(distance_threshold=distance_threshold,
                                                        match_filter=match_filter,
                                                        token_size=token_size,
                                                        sample_length=sample_length)

    def set_engine(self, engine):
        self.engine = engine

    def set_kb(self, kb):
        kb.soft_404_responses = self.soft_404_responses

    def load_kb(self, kb):
        self.soft_404_responses = kb.soft_404_responses

    def set_child_heuristics(self, heuristics):
        self.child_heuristics = heuristics

    async def on_request_successful(self, entry):
        entry.result.soft404 = False
        if entry.response.code != 404:
            # We want to apply this logic to any URI that provides the same output regardless of the path provided.
            # However this makes no sense when the server tells us it does not exist, so skil this case.
            entry.result.soft404 = await self.is_soft_404(entry.request.url, entry.response)

    async def is_soft_404(self, url, response):
        if self._is_home(url):
            return False

        # Before fetching a new 404 sample for a specific path, verify if the currently
        # obtained paths do not already have a matching sample. This will avoid multiple
        # requests per sub-path and extension when a catch-all already exists.
        for potential_target in self.enumerate_candidates(url):
            candidate = await self.get_soft_404_sample(potential_target, fetch_missing=False)
            if self.signature_comparator.match_list(response, candidate, url=url):
                return True

        # Fully perform, fetching as required
        soft_404_response = await self.get_soft_404_sample(url)

        if soft_404_response is None:
            raise RejectRequest("Impossible to obtain required sample. Cannot confirm result validity.")

        is_soft_404 = self.signature_comparator.match_list(response, soft_404_response, url=url)

        return is_soft_404

    async def get_soft_404_sample(self, url, *, fetch_missing=True):
        server_address = urljoin(url, "/")
        if self._is_home(url):
            return None

        # If we have a match, leave right away
        request_url_pattern = self._extract_pattern_from_url(url)
        if request_url_pattern in self.soft_404_responses[server_address]:
            return self.soft_404_responses[server_address][request_url_pattern]

        if not fetch_missing:
            return None

        if request_url_pattern not in self.performed[server_address]:
            try:
                # Temporarily assign a future to make sure work is not done twice
                self.performed[server_address][request_url_pattern] = asyncio.Future()
                response = await self._collect_sample(url, request_url_pattern)
                self.soft_404_responses[server_address][request_url_pattern] = response
            except (StopRequest, RejectRequest) as e:
                self.soft_404_responses[server_address][request_url_pattern] = None
            finally:
                # Remove the wait lock
                self.performed[server_address][request_url_pattern].set_result(True)
                self.performed[server_address][request_url_pattern] = None
        elif self.performed[server_address][request_url_pattern] is not None:
            await self.performed[server_address][request_url_pattern]
        return self.soft_404_responses[server_address][request_url_pattern]

    def _is_home(self, url):
        server_address = urljoin(url, "/")
        return url == server_address

    async def _collect_sample(self, url, url_pattern):
        """
        Sample collection is meant to be very tolerant to generic failures as failing to
        obtain the sample has important consequences on the results.

        - Multiple retries with longer delays
        - Larger than usual timeout
        """
        samples = []

        urls = [self._create_random_url(url, url_pattern) for _ in range(self.confirmation_factor)]
        iterator = asyncio.as_completed([self._fetch_sample(url) for url in urls])
        for promise in iterator:
            try:
                sig = await promise
                if sig:
                    samples.append(sig)
            except RejectRequest:
                pass

        if not samples:
            raise StopRequest("Impossible to obtain sample")
        else:
            return samples

    async def _fetch_sample(self, url):
        for x in range(5):
            try:
                request = Entry.create(url, arguments={"timeout": 10})
                result = await self.engine.perform_high_priority(request, self.child_heuristics)

                sig = self.signature_comparator.from_entry(result)
                return sig
            except StopRequest:
                await asyncio.sleep(self.collect_retry_delay)

        return None

    def enumerate_candidates(self, url):
        parts = urlparse(url)
        path = parts.path
        while len(path) > 1:
            yield urljoin(url, path)
            yield urljoin(url, path) + "/"
            path, _ = os.path.split(path)

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


class SignatureComparator:

    def __init__(self, distance_threshold=5, match_filter=DEFAULT_FILTER, token_size=4, sample_length=5120):
        self.distance_threshold = distance_threshold
        self.match_filter = match_filter
        self.token_size = token_size
        self.sample_length = sample_length

    def from_entry(self, entry):
        response = entry.response
        return ContentSignature(code=response.code,
                                content_simhash=self._simhash(response),
                                content_hash=self._hash(response),
                                content_sample=self._sample(response.raw, entry.request.url))

    def _hash(self, response):
        return hashlib.md5(response.raw).digest()

    def _simhash(self, response):
        try:
            return Simhash(response.content, filter=self.match_filter, token_size=self.token_size).value
        except UnicodeDecodeError:  # Response content is not text, store the hash of the raw data:
            return None

    def _sample(self, response, request_url):
        return response[0:self.sample_length]

    def match(self, response, signature, *, url):
        if signature is None:
            return False

        current = ContentSignature(code=response.code)

        if current.code == signature.code:
            current.content_hash = self._hash(response)
            if signature.content_hash is not None and signature.content_hash == current.content_hash:
                return True

            current.content_simhash = self._simhash(response)
            if signature.match_simhash(current, self.distance_threshold):
                return True

            if self.sample_length > 0:
                current.content_sample = self._sample(response.raw, url)
                if signature.match_sample(current):
                    return True

        return False

    def match_list(self, response, signature_list, *, url):
        if signature_list is None:
            return False

        signature_list = signature_list if isinstance(signature_list, list) else [signature_list]

        for signature in signature_list:
            if self.match(response, signature, url=url):
                return True

        return False


class ContentSignature:

    def __init__(self, *, code, content_hash=None, content_sample=None, content_simhash=None):
        self.code = code
        self.content_hash = content_hash
        self.content_sample = content_sample
        self.content_simhash = content_simhash

    def match_sample(self, other):
        if self.content_sample is None or other.content_sample is None:
            return False

        matcher = SequenceMatcher(a=self.content_sample, b=other.content_sample,
                                  isjunk=None, autojunk=False)

        # This content is almost similar to a generated 404, therefore it's a 404.
        return matcher.ratio() > 0.8

    def match_simhash(self, other, distance_threshold):
        if self.content_simhash is None or other.content_simhash is None:
            return False

        resp_hash = Simhash(other.content_simhash)
        distance = resp_hash.distance(Simhash(self.content_simhash))
        return distance < distance_threshold

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
