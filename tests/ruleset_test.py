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
from unittest.mock import MagicMock, patch

from fixtures import async_test
from hammertime.ruleset import RuleSet, Heuristics, StopRequest
from hammertime.http import Entry
from aiohttp.test_utils import make_mocked_coro
import asyncio


class RuleSetTest(TestCase):

    @async_test()
    async def test_empty_ruleset(self):
        rs = RuleSet()
        self.assertIsNone(await rs.accept(Entry.create('http://example.com')))
        self.assertEqual(0, len(rs))

    @async_test()
    async def test_rules_triggered(self, fake_future):
        r1 = make_mocked_coro(return_value=fake_future(None))
        r2 = make_mocked_coro(return_value=fake_future(None))

        rs = RuleSet()
        with patch('asyncio.iscoroutinefunction', MagicMock(return_value=True)):
            rs.add(r1)
            rs.add(r2)
            self.assertEqual(2, len(rs))

            entry = Entry.create('http://example.com')

            await rs.accept(entry)

            r1.assert_called_with(entry)
            r2.assert_called_with(entry)

    @async_test()
    async def test_failure_interrupts(self, fake_future):
        r1 = make_mocked_coro(raise_exception=StopRequest())
        r2 = make_mocked_coro()

        rs = RuleSet()
        with patch('asyncio.iscoroutinefunction', MagicMock(return_value=True)):
            rs.add(r1)
            rs.add(r2)

            entry = Entry.create('http://example.com')

            with self.assertRaises(StopRequest):
                await rs.accept(entry)

            r1.assert_called_with(entry)
            r2.assert_not_called()


class HeuristicsTest(TestCase):

    def test_load_heuristics(self):
        a = HeuristicA()
        b = HeuristicB()

        h = Heuristics()
        h.add(a)
        h.add(b)
        self.assertEqual(len(h.rulesets["before_request"]), 2)
        self.assertEqual(len(h.rulesets["after_headers"]), 1)
        self.assertEqual(len(h.rulesets["after_response"]), 1)
        self.assertEqual(h.rulesets["before_request"].accept, h.before_request)

    def test_load_multiple_heuristics(self):
        a = HeuristicA()
        b = HeuristicB()

        h = Heuristics()
        h.add_multiple([a, b])
        self.assertEqual(len(h.rulesets["before_request"]), 2)
        self.assertEqual(len(h.rulesets["after_headers"]), 1)
        self.assertEqual(len(h.rulesets["after_response"]), 1)
        self.assertEqual(h.rulesets["before_request"].accept, h.before_request)

    def test_load_bad_heuristic(self):
        a = HeuristicBad()

        h = Heuristics()
        with self.assertRaises(ValueError):
            h.add(a)

    def test_load_not_async(self):
        a = HeuristicNonAsync()

        h = Heuristics()
        with self.assertRaises(ValueError):
            h.add(a)

    def test_assign_engine_and_kb_on_heuristics(self):
        a = HeuristicA()
        b = HeuristicB()

        h = Heuristics(request_engine="X", kb="Y")
        h.add_multiple([a, b])
        self.assertEqual(a.engine_set, "X")
        self.assertEqual(b.kb_set, "Y")

    def test_do_not_override_with_none(self):
        a = HeuristicA()
        b = HeuristicB()

        h = Heuristics()
        h.add_multiple([a, b])
        self.assertEqual(a.engine_set, "NO")
        self.assertEqual(b.kb_set, "NO")


class HeuristicBad:
    pass


class HeuristicNonAsync:
    def before_request(self, entry):
        pass


class HeuristicA:

    engine_set = "NO"

    def set_engine(self, engine):
        self.engine_set = engine

    async def before_request(self, entry):
        pass

    async def after_headers(self, entry):
        pass


class HeuristicB:

    kb_set = "NO"

    def set_kb(self, kb):
        self.kb_set = kb

    async def before_request(self, entry):
        pass

    async def after_response(self, entry):
        pass
