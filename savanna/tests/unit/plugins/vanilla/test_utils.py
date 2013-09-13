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

from savanna.conductor import resource as r
from savanna.plugins.general import utils as u


class VanillaUtilsTest(unittest2.TestCase):
    def setUp(self):
        i1 = _make_inst_dict('i1', 'master')
        i2 = _make_inst_dict('i2', 'worker1')
        i3 = _make_inst_dict('i3', 'worker2')
        i4 = _make_inst_dict('i4', 'worker3')
        i5 = _make_inst_dict('i5', 'sn')

        ng1 = _make_ng_dict("master", "f1", ["jt", "nn"], 1, [i1])
        ng2 = _make_ng_dict("workers", "f1", ["tt", "dn"], 3,
                            [i2, i3, i4])
        ng3 = _make_ng_dict("sn", "f1", ["dn"], 1, [i5])

        self.c1 = _create_cluster("cluster1", "tenant1", "vanilla", "1.2.1",
                                  [ng1, ng2, ng3])

        self.ng1 = self.c1.node_groups[0]
        self.ng2 = self.c1.node_groups[1]
        self.ng3 = self.c1.node_groups[2]

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
        self.assertEqual(len(u.get_instances(self.c1)), 5)
        self.assertListEqual(u.get_instances(self.c1, 'wrong-process'), [])
        self.assertListEqual(u.get_instances(self.c1, 'nn'),
                             self.ng1.instances)
        instances = list(self.ng2.instances)
        instances += self.ng3.instances
        self.assertListEqual(u.get_instances(self.c1, 'dn'), instances)

    def test_generate_lines_from_list(self):
        self.assertEqual(u.generate_host_names(self.ng2.instances),
                         "worker1\nworker2\nworker3")
        self.assertEqual(u.generate_host_names([]), "")


def _create_cluster(name, tenant, plugin, version, node_groups, **kwargs):
    dct = {'name': name, 'tenant_id': tenant, 'plugin_name': plugin,
           'hadoop_version': version, 'node_groups': node_groups}
    dct.update(kwargs)
    return r.ClusterResource(dct)


def _make_ng_dict(name, flavor, processes, count, instances=[]):
    return {'name': name, 'flavor_id': flavor, 'node_processes': processes,
            'count': count, 'instances': instances}


def _make_inst_dict(inst_id, inst_name):
    return {'instance_id': inst_id, 'instance_name': inst_name}
