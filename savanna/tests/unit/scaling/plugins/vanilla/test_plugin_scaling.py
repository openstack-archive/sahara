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

import unittest2

from savanna.db import models as m
from savanna.plugins.vanilla import exceptions as ex
from savanna.plugins.vanilla import plugin as p


class VanillaPluginScalingTest(unittest2.TestCase):
    def setUp(self):
        self.pl = p.VanillaProvider()
        self.cl = m.Cluster("cluster1", "tenant1", "vanilla", "1.1.2")
        self.ng1 = m.NodeGroup("nn", "f1", ["namenode"], 1)
        self.ng2 = m.NodeGroup("jt", "f1", ["jobtracker"], 1)
        self.ng3 = m.NodeGroup("tt", "f1", ["tasktracker"], 10)
        self.cl_configs = self.pl.get_configs("1.1.2")

    def test_validate_scaling(self):
        ng_names = {self.ng1.name: 1, self.ng2.name: 1, self.ng3.name: 10}
        self.cl.node_groups.append(self.ng1)
        self.cl.node_groups.append(self.ng2)
        self.cl.node_groups.append(self.ng3)
        with self.assertRaises(ex.NodeGroupCannotBeScaled):
            self.pl.validate_scaling(self.cl, ng_names, [self.ng1])
        del ng_names['jt']
        del ng_names['nn']
        ng_names['dn'] = 3
        with self.assertRaises(ex.NodeGroupsDoNotExist):
            self.pl.validate_scaling(self.cl, ng_names, [self.ng3])
