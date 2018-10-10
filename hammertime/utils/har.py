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


from http.client import responses

from marshmallow_har import HAR, Entry, Request, Response, Content, Header, Creator
from hammertime.__version__ import __version__


class HammerTimeToHAR:

    def convert_entries(self, entries, *, creator=None):
        out = HAR(creator=creator or Creator(name="HammerTime", version=__version__))
        for e in entries:
            if e.result.redirects:
                for sub in e.result.redirects:
                    out.entries.append(self.convert_entry(sub))
            else:
                out.entries.append(self.convert_entry(e))
        return out

    def convert_entry(self, entry):
        out = Entry(request=self.convert_request(entry.request))

        if entry.response:
            out.response = self.convert_response(entry.response)

        return out

    def convert_headers(self, headers):
        return [Header(name=k, value=v) for k, v in headers.items()]

    def convert_request(self, request):
        out = Request(method=request.method, url=request.url,
                      headers=self.convert_headers(request.headers))

        return out

    def convert_response(self, response):
        out = Response(status=response.code, status_text=self._lookup_code_text(response.code),
                       headers=self.convert_headers(response.headers))
        out.content = Content(text=self._get_content(response))

        headers = {k.lower(): v for k, v in response.headers.items()}
        out.content.mime_type = headers.get('content-type')
        out.content.size = int(headers.get('size', -1))

        return out

    def _get_content(self, response):
        try:
            return response.content
        except UnicodeDecodeError:
            return response.raw.decode("utf-8", "surrogateescape")

    @staticmethod
    def _lookup_code_text(code):
        return responses.get(code) or "Unknown"
