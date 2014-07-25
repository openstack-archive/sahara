# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Base class for classes that need modular database access."""

from oslo.config import cfg

from sahara.openstack.common import importutils


db_driver_opt = cfg.StrOpt('db_driver',
                           default='sahara.db',
                           help='Driver to use for database access.')

CONF = cfg.CONF
CONF.register_opt(db_driver_opt)


class Base(object):
    """DB driver is injected in the init method."""

    def __init__(self):
        self.db = importutils.import_module(CONF.db_driver)
