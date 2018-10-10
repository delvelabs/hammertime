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

import unittest
import asyncio
from functools import wraps
from aiohttp.test_utils import loop_context

from easyinject import Injector
from hammertime.ruleset import Heuristics
from hammertime.kb import KnowledgeBase

try:
    from freezegun import freeze_time
except ImportError:
    def freeze_time(time):
        def setup(f):
            return unittest.skip("freezegun is required")(f)

        return setup


class Pipeline:

    def __init__(self, *, engine=None):
        self.kb = KnowledgeBase()
        self.heuristics = Heuristics(kb=self.kb, request_engine=engine)
        self.child_heuristics = Heuristics(kb=self.kb, request_engine=engine)

    def add(self, heuristic, *, with_child=False):
        self.heuristics.add(heuristic)

        if with_child:
            self.child_heuristics.add(heuristic)

    async def perform_ok(self, entry):
        await self.heuristics.before_request(entry)
        await self.heuristics.after_headers(entry)
        await self.heuristics.after_response(entry)
        await self.heuristics.on_request_successful(entry)


def async_test():
    def setup(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            with loop_context() as loop:
                injector = Injector(loop=loop,
                                    fake_future=lambda: fake_future)
                asyncio.get_child_watcher().attach_loop(loop)
                asyncio.set_event_loop(loop)
                loop.run_until_complete(injector.call(f, *args, **kwargs))
        return wrapper
    return setup


def fake_future(result, loop):
    f = asyncio.Future(loop=loop)
    f.set_result(result)
    return f
