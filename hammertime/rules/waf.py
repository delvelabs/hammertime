# hammertime: A high-volume http fetch library
# Copyright (C) 2018-  Delve Labs inc.
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


from hammertime.ruleset import RejectRequest


class RejectWebApplicationFirewall:
    """
    We would normally expect WAFs to be handled by generic directives, such as rejecting status codes
    or various behavior change detections. However, some of them simply misbehave, so we are forced
    to have custom rules.
    """

    # Found to return 200 codes with a long unique identifier that prevents the behavior detections from
    # working properly.
    bigip_asm = b"<body>The requested URL was rejected. Please consult with your administrator.<br>"

    async def after_response(self, entry):
        if self.bigip_asm in entry.response.raw:
            raise RejectRequest("BIG-IP ASM Triggered")
