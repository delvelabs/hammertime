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
import re
import random
import string

from ..ruleset import RejectRequest, StopRequest
from ..http import Entry
from .sampling import SignatureComparator


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

    def __init__(self, distance_threshold=5,
                 collect_retry_delay=5.0, confirmation_factor=1,
                 tail_lookup=True):
        self.engine = None
        self.performed = defaultdict(dict)
        self.confirmation_factor = confirmation_factor
        self.soft_404_responses = defaultdict(dict)
        self.collect_retry_delay = collect_retry_delay
        self.signature_comparator = SignatureComparator(distance_threshold=distance_threshold)
        self.path_generator = SimilarPathGenerator()

        if not tail_lookup:
            self.path_generator.get_tail_pattern = lambda url, tail: None

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
            entry.result.soft404 = await self.is_soft_404(entry.request.url, entry)

    async def is_soft_404(self, url, entry):
        if self._is_home(url):
            return False

        # Before fetching a new 404 sample for a specific path, verify if the currently
        # obtained paths do not already have a matching sample. This will avoid multiple
        # requests per sub-path and extension when a catch-all already exists.
        for potential_target in self.enumerate_candidates(url):
            candidate = await self.get_soft_404_sample(potential_target,
                                                       pattern=self.path_generator.get_pattern(potential_target),
                                                       fetch_missing=False)
            if self.signature_comparator.match_list(entry, candidate, url=url):
                return True

        if await self._tail_matches(entry):
            return True

        # Fully perform, fetching as required
        soft_404_response = await self.get_soft_404_sample(url, pattern=self.path_generator.get_pattern(url))
        tail_response_a = await self.get_soft_404_sample(url,
                                                         pattern=self.path_generator.get_tail_pattern(url, tail="\\l"))
        tail_response_b = await self.get_soft_404_sample(url,
                                                         pattern=self.path_generator.get_tail_pattern(url, tail=".\\l"))

        if self.signature_comparator.match_list(entry, soft_404_response, url=url):
            return True

        # We also want to catch prefix-based rules for which all paths with a common suffix respond with the same
        if self.signature_comparator.match_list(entry, tail_response_a, url=url):
            return True

        if self.signature_comparator.match_list(entry, tail_response_b, url=url):
            return True

        if soft_404_response is None:
            raise RejectRequest("Impossible to obtain required sample. Cannot confirm result validity.")

        return False

    async def _tail_matches(self, entry):
        url = entry.request.url

        # We want to catch if the tail pattern matches parent paths. Common example:
        # /login has a catch-all rule
        # /loginuser, login.tar.gz and others all respond with the same page as /login
        tail_start = url.rfind("/")
        for i in range(tail_start + 2, len(url)):
            potential_target = url[0:i]

            # Any character not part of a valid prefix is ignored.
            if potential_target[-1] not in self.path_generator.tail_chars:
                break

            # Check if we know these patterns without fetching
            # The addition to kb on found paths happens by the post-request process
            pattern = potential_target + "\\l"
            candidate = await self.get_soft_404_sample(potential_target,
                                                       pattern=pattern,
                                                       fetch_missing=False)
            if self.signature_comparator.match_list(entry, candidate, url=url):
                return True

            pattern = potential_target + ".\\l"
            candidate = await self.get_soft_404_sample(potential_target,
                                                       pattern=pattern,
                                                       fetch_missing=False)
            if self.signature_comparator.match_list(entry, candidate, url=url):
                return True

        return False

    async def get_soft_404_sample(self, url, *, pattern, fetch_missing=True):
        server_address = urljoin(url, "/")
        if self._is_home(url) or pattern is None:
            return None

        # If we have a match, leave right away
        if pattern in self.soft_404_responses[server_address]:
            return self.soft_404_responses[server_address][pattern]

        if not fetch_missing:
            return None

        if pattern not in self.performed[server_address]:
            try:
                # Temporarily assign a future to make sure work is not done twice
                self.performed[server_address][pattern] = asyncio.Future()
                response = await self._collect_sample(url, pattern)
                self.soft_404_responses[server_address][pattern] = response
            except (StopRequest, RejectRequest):
                self.soft_404_responses[server_address][pattern] = None
            finally:
                # Remove the wait lock
                self.performed[server_address][pattern].set_result(True)
                self.performed[server_address][pattern] = None
        elif self.performed[server_address][pattern] is not None:
            await self.performed[server_address][pattern]
        return self.soft_404_responses[server_address][pattern]

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

        urls = [self.path_generator.generate_url(url, url_pattern) for _ in range(self.confirmation_factor)]

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


class RejectSoft404:

    async def on_request_successful(self, entry):
        if entry.result.soft404:
            raise RejectRequest("Response to %s is a soft 404." % entry.request)


class SimilarPathGenerator:
    tail_pattern = re.compile(r'/([a-z-]+)((\.[a-z0-9\.]*[a-z0-9])|/)$')
    tail_chars = set("abcdefghijklmnopqrstuvwxyz-")

    def get_pattern(self, url):
        """Return the path part of the URL with the last element replaced with its pattern in a regex-like format:
        \\l -> lowercase letters, same as [a-z]+
        \\L -> uppercase letters, same as [A-Z]+
        \\i -> letters ignoring case, same as [a-zA-Z]+
        \\d -> digits, same as \\d+
        \\w -> word characters (letters, digits, underscores), same as \\w+
        All other characters match themselves
        """
        path = urlparse(url).path
        directories, filename = os.path.split(path)
        if len(filename) > 0:
            pattern = self.get_pattern_for_filename(filename)
            if directories[-1] != "/":
                directories += "/"
            return directories + pattern
        else:
            return self.get_pattern_for_directory(directories)

    def get_tail_pattern(self, url, tail="\\l"):
        path = urlparse(url).path
        out = self.tail_pattern.sub(r"/\1" + tail.replace("\\", "\\\\"), path)
        if path != out:
            return urljoin(url, out)
        else:
            return None

    def generate_url(self, url, path):
        replace_patterns = ["\\l", "\\L", "\\i", "\\d", "\\w"]
        for pattern in replace_patterns:
            path = path.replace(pattern, self._create_random_string(pattern, random.randint(8, 15)))
        return urljoin(url, path)

    def _create_random_string(self, pattern, length):
        choices = None
        if pattern == "\\l":
            choices = string.ascii_lowercase
        elif pattern == "\\L":
            choices = string.ascii_uppercase
        elif pattern == "\\i":
            choices = string.ascii_letters
        elif pattern == "\\w":
            choices = string.ascii_letters + string.digits + "_"
        elif pattern == "\\d":
            choices = string.digits
        if choices is not None:
            return "".join([random.choice(choices) for _ in range(length)])
        else:
            return ""

    def get_pattern_for_directory(self, directory_path):
        if directory_path == "/":
            return "/"
        directory_path = directory_path.strip("/")
        directories = directory_path.split("/")
        if len(directories) > 1:
            directory_pattern = self._create_pattern_from_string(directories[-1])
            return "/%s/%s/" % ("/".join(directories[:-1]), directory_pattern)
        else:
            return "/%s/" % self._create_pattern_from_string(directories[0])

    def get_pattern_for_filename(self, filename):
        filename, extension = os.path.splitext(filename)
        return self._create_pattern_from_string(filename) + extension

    def _create_pattern_from_string(self, string):
        parts = re.split("\\W", string)
        pattern = re.sub("\\w+", "{}", string)
        pattern_list = []
        for part in parts:
            if len(part) > 0:
                if re.fullmatch("[a-z]+", part):
                    pattern_list.append("\\l")
                elif re.fullmatch("[A-Z]+", part):
                    pattern_list.append("\\L")
                elif re.fullmatch("[a-zA-Z]+", part):
                    pattern_list.append("\\i")
                elif re.fullmatch("\\d+", part):
                    pattern_list.append("\\d")
                else:
                    pattern_list.append("\\w")
        return pattern.format(*pattern_list)
