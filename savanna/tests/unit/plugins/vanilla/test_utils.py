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
from savanna.plugins.vanilla import utils as u


class VanillaUtilsTest(unittest2.TestCase):
    def setUp(self):
        self.c1 = m.Cluster("cluster1", "tenant1", "vanilla", "1.1.2")
        self.ng1 = m.NodeGroup("master", "f1", ["jt", "nn"], 1)
        self.ng2 = m.NodeGroup("workers", "f1", ["tt", "dn"], 3)
        self.ng3 = m.NodeGroup("sn", "f1", ["dn"], 1)
        self.c1.node_groups = [self.ng1, self.ng2, self.ng3]

        self.ng1.instances = [m.Instance("ng1", "i1", "master")]
        self.ng2.instances = [m.Instance("ng2", "i2", "worker1"),
                              m.Instance("ng2", "i3", "worker2"),
                              m.Instance("ng2", "i4", "worker3")]
        self.ng3.instances = [m.Instance("ng3", "i5", "sn")]

    def test_get_node_groups(self):
        self.assertListEqual(u.get_node_groups(self.c1), self.c1.node_groups)
        self.assertListEqual(u.get_node_groups(self.c1, ["wrong-process"]), [])
        self.assertListEqual(u.get_node_groups(self.c1, ['dn', 'tt']),
                             [self.ng2])
        self.assertListEqual(u.get_node_groups(self.c1, 'dn'),
                             [self.ng2, self.ng3])
        self.assertListEqual(u.get_node_groups(self.c1, ['dn']),
                             [self.ng2, self.ng3])
        self.assertListEqual(u.get_node_groups(self.c1, ['jt', 'tt']), [])

    def test_get_instances(self):
        self.assertEquals(len(u.get_instances(self.c1)), 5)
        self.assertListEqual(u.get_instances(self.c1, 'wrong-process'), [])
        self.assertListEqual(u.get_instances(self.c1, 'nn'),
                             self.ng1.instances)
        self.assertListEqual(u.get_instances(self.c1, 'dn'),
                             self.ng2.instances + self.ng3.instances)

    def test_generate_lines_from_list(self):
        self.assertEquals(u.generate_host_names(self.ng2.instances),
                          "worker1\nworker2\nworker3")
        self.assertEquals(u.generate_host_names([]), "")
