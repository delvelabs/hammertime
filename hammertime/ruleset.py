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


class Heuristics:

    EVENTS = {"before_request", "after_headers", "after_response"}

    def __init__(self):
        self.rulesets = {event: RuleSet() for event in self.EVENTS}

        for key, rs in self.rulesets.items():
            setattr(self, key, rs.accept)

    def add_multiple(self, iterator):
        for h in iterator:
            self.add(h)

    def add(self, heuristic):
        applied = False
        supported = dir(heuristic)
        for event in self.EVENTS:
            if event in supported:
                self.rulesets[event].add(getattr(heuristic, event))
                applied = True

        if not applied:
            raise ValueError("Expecting heuristic to support some of %s" % self.EVENTS)


class RuleSet:

    def __init__(self):
        self.rules = []

    def add(self, rule):
        if not asyncio.iscoroutinefunction(rule):
            raise ValueError("Expecting asyncio coroutine for %s" % rule)

        self.rules.append(rule)

    def __len__(self):
        return len(self.rules)

    async def accept(self, entry):
        for r in self.rules:
            await r(entry)


class HammerTimeException(Exception):
    pass


class StopRequest(HammerTimeException):
    pass


class RejectRequest(HammerTimeException):
    pass
