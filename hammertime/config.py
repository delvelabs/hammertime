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
import logging
from easyinject import Injector

from .engine import AioHttpEngine
from .kb import KnowledgeBase


def custom_event_loop():
    try:
        import uvloop
        loop = uvloop.new_event_loop()
        asyncio.set_event_loop(loop)

        logger = logging.getLogger(__name__)
        logger.debug('Using uvloop')
    except ImportError:
        pass

    return asyncio.get_event_loop()


defaults = Injector(loop=custom_event_loop,
                    request_engine=AioHttpEngine,
                    kb=KnowledgeBase)
