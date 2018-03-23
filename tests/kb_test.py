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

from hammertime.kb import KnowledgeBase


class KnowledgeBaseTest(TestCase):

    def test_check_for_initialized_content(self):
        kb = KnowledgeBase()
        self.assertNotIn("random_entry", kb)

        with self.assertRaises(AttributeError):
            kb.random_entry

    def test_assign_entry(self):
        kb = KnowledgeBase()
        kb.random_entry = PieceOfData(123)
        self.assertIn("random_entry", kb)
        self.assertEqual(kb.random_entry.counter, 123)

    def test_assign_entry_twice_causes_error(self):
        kb = KnowledgeBase()
        kb.random_entry = PieceOfData(123)

        with self.assertRaises(AttributeError):
            kb.random_entry = PieceOfData(456)

        self.assertEqual(kb.random_entry.counter, 123)


class PieceOfData:

    def __init__(self, value):
        self.counter = value
