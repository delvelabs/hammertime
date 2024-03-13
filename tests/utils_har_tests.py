# hammertime: A high-volume http fetch library
# Copyright (C) 2017-  Delve Labs inc.
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
from hammertime.utils.har import HammerTimeToHAR
from hammertime.http import Entry, StaticResponse
from marshmallow_har import Header


class Matcher:
    def __init__(self, compare):
        self.compare = compare

    def __eq__(self, other):
        return self.compare(other)


class HammerTimeToHARConversion(TestCase):

    def setUp(self):
        self.conv = HammerTimeToHAR()

    def test_convert_request_only(self):
        ht = Entry.create("http://example.com/")

        har = self.conv.convert_entry(ht)
        self.assertEqual(har.request.method, "GET")
        self.assertEqual(har.request.url, "http://example.com/")

    def test_convert_request_with_headers(self):
        ht = Entry.create("http://example.com/", headers={
            "Accept": "text/plain",
            "If-Modified-Since": "yesterday",
        })

        har = self.conv.convert_entry(ht)
        self.assertIn(Header(name="Accept", value="text/plain"), har.request.headers)
        self.assertIn(Header(name="If-Modified-Since", value="yesterday"), har.request.headers)

    def test_convert_response(self):
        ht = Entry.create("http://example.com/",
                          response=StaticResponse(code=405, content="hello", headers={}))

        har = self.conv.convert_entry(ht)
        self.assertEqual(har.response.content.text, "hello")
        self.assertEqual(har.response.content.size, -1)
        self.assertEqual(har.response.content.mime_type, None)
        self.assertEqual(har.response.status, 405)
        self.assertEqual(har.response.status_text, "Method Not Allowed")

    def test_convert_response_with_headers(self):
        ht = Entry.create("http://example.com/",
                          response=StaticResponse(code=200, content="hello", headers={
                              "Content-Type": "text/plain",
                              "Size": "5",
                          }))

        har = self.conv.convert_entry(ht)
        har.__class__.load(har.dump())
        self.assertEqual(har.response.status, 200)
        self.assertEqual(har.response.status_text, "OK")
        self.assertEqual(har.response.content.text, "hello")
        self.assertEqual(har.response.content.mime_type, "text/plain")
        self.assertEqual(har.response.content.size, 5)
        self.assertIn(Header(name="Size", value="5"), har.response.headers)

    def test_convert_response_with_non_standard_code(self):
        ht = Entry.create("http://example.com/",
                          response=StaticResponse(code=599, content="hello", headers={}))

        har = self.conv.convert_entry(ht)
        self.assertEqual(har.response.status, 599)
        self.assertEqual(har.response.status_text, "Unknown")

    def test_convert_sequence_to_har(self):
        sequence = [Entry.create("http://example.com/"),
                    Entry.create("http://example.com/a/"),
                    Entry.create("http://example.com/b/")]
        har = self.conv.convert_entries(sequence)
        self.assertEqual(["http://example.com/", "http://example.com/a/", "http://example.com/b/"],
                         [e.request.url for e in har.entries])

    def test_expand_redirects(self):
        entry = Entry.create("http://example.com/", response=StaticResponse(code=200, content="hello", headers={}))
        entry.result.redirects = [
            Entry.create("http://example.com/", response=StaticResponse(code=302, headers={
                "Location": "http://example.com/a/",
            })),
            Entry.create("http://example.com/a/", response=StaticResponse(code=302, headers={
                "Location": "http://example.com/b/",
            })),
            Entry.create("http://example.com/b/", response=StaticResponse(code=200, content="hello", headers={})),
        ]
        har = self.conv.convert_entries([entry])
        self.assertEqual(["http://example.com/", "http://example.com/a/", "http://example.com/b/"],
                         [e.request.url for e in har.entries])
