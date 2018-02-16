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

from uuid import uuid4
from urllib.parse import urlparse, urljoin

from hammertime.http import Entry
from .redirects import valid_redirects
from hammertime.ruleset import RejectRequest


class RejectCatchAllRedirect:

    def __init__(self):
        self.engine = None

    def set_engine(self, engine):
        self.engine = engine

    async def before_request(self, entry):
        url = entry.request.url
        path = urlparse(url).path
        prefix = path.split("/")[:-1]
        random_path = "/".join(prefix) + "/" + str(uuid4())
        _entry = await self.engine.perform_high_priority(Entry.create(urljoin(url, random_path)))
        if _entry.response.code in valid_redirects:
            try:
                redirect = _entry.response.headers["location"]
                if redirect == url:
                    raise RejectRequest("%s redirected to a catch all redirect" % url)
            except KeyError:
                pass
