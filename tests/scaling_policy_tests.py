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
from fixtures import async_test

from hammertime.engine.scaling import SlowStartPolicy


class ScalingPolicyTest(unittest.TestCase):

    @async_test()
    async def test_initial_scale_target(self):
        policy = SlowStartPolicy(initial=3)
        assert policy.concurrency == 3

    @async_test()
    async def test_several_stable_cohorts_increase_concurrency(self):
        policy = SlowStartPolicy(initial=3, cohort_size=1)
        await policy.record(duration=10.5)
        await policy.record(duration=10.5)
        await policy.record(duration=10.5)

        assert policy.concurrency > 3

    @async_test()
    async def test_initial_cohort_cannot_cause_change(self):
        policy = SlowStartPolicy(initial=3, cohort_size=1)
        await policy.record(duration=10.5)

        assert policy.concurrency == 3

    @async_test()
    async def test_intermim_cohorts_get_discarded(self):
        policy = SlowStartPolicy(initial=3, cohort_size=1)
        _ = await policy.record(duration=15)   # Discard
        _ = await policy.record(duration=10.5)  # Stay
        c = await policy.record(duration=10.5)  # Scale up
        d = await policy.record(duration=11.5)  # Discard
        e = await policy.record(duration=10.5)  # Scale up

        assert c == d and e > d

    @async_test()
    async def test_slight_increase_in_time_is_tolerated(self):
        policy = SlowStartPolicy(initial=3, cohort_size=1)
        _ = await policy.record(duration=15)   # Discard
        _ = await policy.record(duration=10.5)  # Stay
        _ = await policy.record(duration=10.5)  # Scale up
        d = await policy.record(duration=11.5)  # Discard
        e = await policy.record(duration=10.508)  # Scale up

        assert e > d

    @async_test()
    async def test_slight_decrease_is_accepted(self):
        policy = SlowStartPolicy(initial=3, cohort_size=1)
        _ = await policy.record(duration=15)   # Discard
        _ = await policy.record(duration=10.5)  # Stay
        _ = await policy.record(duration=10.5)  # Scale up
        d = await policy.record(duration=11.5)  # Discard
        e = await policy.record(duration=10.498)  # Scale up

        assert e > d

    @async_test()
    async def test_large_increase_reverts(self):
        policy = SlowStartPolicy(initial=3, cohort_size=1)
        _ = await policy.record(duration=15)   # Discard
        b = await policy.record(duration=10.5)  # Stay
        c = await policy.record(duration=10.5)  # Scale up
        d = await policy.record(duration=11.5)  # Discard
        e = await policy.record(duration=12.7)  # Backtrack / cooldown

        assert c == d and b > e

    @async_test()
    async def test_not_scaling_back_up_after_ceiling_reached(self):
        policy = SlowStartPolicy(initial=3, cohort_size=1)
        _ = await policy.record(duration=15)   # Discard
        b = await policy.record(duration=10.5)  # Stay
        _ = await policy.record(duration=10.5)  # Scale up
        _ = await policy.record(duration=11.5)  # Discard
        e = await policy.record(duration=12.7)  # Backtrack / cooldown
        _ = await policy.record(duration=10.7)  # Discard
        g = await policy.record(duration=10.5)  # Scale back up
        h = await policy.record(duration=10.5)  # Stay

        assert b > e and b > g and g == h
