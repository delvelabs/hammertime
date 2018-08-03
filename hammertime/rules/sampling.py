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

import hashlib
from difflib import SequenceMatcher

from .simhash import Simhash, DEFAULT_FILTER


class ContentHashSampling:

    def __init__(self, hash_method=hashlib.md5):
        self._hash_method = hash_method

    async def after_response(self, entry):
        entry.result.content_hash = self._hash(entry.response)

    def _hash(self, response):
        return self._hash_method(response.raw).digest()


class ContentSimhashSampling:

    def __init__(self, match_filter=DEFAULT_FILTER, token_size=4):
        self.match_filter = match_filter
        self.token_size = token_size

    async def after_response(self, entry):
        entry.result.content_simhash = self._simhash(entry.response)

    def _simhash(self, response):
        try:
            return Simhash(response.content, filter=self.match_filter, token_size=self.token_size)
        except UnicodeDecodeError:  # Response content is not text, store the hash of the raw data:
            return None


class ContentSampling:

    def __init__(self,  sample_length=5120):
        self.sample_length = sample_length

    async def after_response(self, entry):
        entry.result.content_sample = self._sample(entry.response.raw, entry.request.url)

    def _sample(self, response, request_url):
        return response[0:self.sample_length]


class SignatureComparator:

    def __init__(self, distance_threshold=5):
        self.distance_threshold = distance_threshold

    def from_entry(self, entry):
        return ContentSignature(code=entry.response.code,
                                content_simhash=getattr(entry.result, "content_simhash", None),
                                content_hash=getattr(entry.result, "content_hash", None),
                                content_sample=getattr(entry.result, "content_sample", None))

    def match(self, entry, signature, *, url):
        if signature is None:
            return False

        current = self.from_entry(entry)

        if current.code == signature.code:
            if signature.match_hash(current):
                return True

            if signature.match_simhash(current, self.distance_threshold):
                return True

            if signature.match_sample(current):
                return True

        return False

    def match_list(self, entry, signature_list, *, url):
        if signature_list is None:
            return False

        signature_list = signature_list if isinstance(signature_list, list) else [signature_list]

        for signature in signature_list:
            if self.match(entry, signature, url=url):
                return True

        return False


class ContentSignature:

    def __init__(self, *, code, content_hash=None, content_sample=None, content_simhash=None):
        self.code = code
        self.content_hash = content_hash
        self.content_sample = content_sample
        self.content_simhash = content_simhash

    def match_hash(self, other):
        if self.content_hash is None or other.content_hash is None:
            return False

        return self.content_hash == other.content_hash

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

        resp_hash = other.content_simhash
        distance = resp_hash.distance(self.content_simhash)
        return distance < distance_threshold

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
