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

import testtools

from sahara.plugins import exceptions as ex
from sahara.plugins import utils as u
from sahara.tests.unit import testutils as tu


class GeneralUtilsTest(testtools.TestCase):
    def setUp(self):
        super(GeneralUtilsTest, self).setUp()
        i1 = tu.make_inst_dict('i1', 'master')
        i2 = tu.make_inst_dict('i2', 'worker1')
        i3 = tu.make_inst_dict('i3', 'worker2')
        i4 = tu.make_inst_dict('i4', 'worker3')
        i5 = tu.make_inst_dict('i5', 'sn')

        ng1 = tu.make_ng_dict("master", "f1", ["jt", "nn"], 1, [i1])
        ng2 = tu.make_ng_dict("workers", "f1", ["tt", "dn"], 3,
                              [i2, i3, i4])
        ng3 = tu.make_ng_dict("sn", "f1", ["dn"], 1, [i5])

        self.c1 = tu.create_cluster("cluster1", "tenant1", "general", "1.2.1",
                                    [ng1, ng2, ng3])

        self.ng1 = self.c1.node_groups[0]
        self.ng2 = self.c1.node_groups[1]
        self.ng3 = self.c1.node_groups[2]

    def test_get_node_groups(self):
        self.assertEqual(u.get_node_groups(self.c1), self.c1.node_groups)
        self.assertEqual(u.get_node_groups(self.c1, "wrong-process"), [])
        self.assertEqual(u.get_node_groups(self.c1, 'dn'),
                         [self.ng2, self.ng3])

    def test_get_instances(self):
        self.assertEqual(len(u.get_instances(self.c1)), 5)
        self.assertEqual(u.get_instances(self.c1, 'wrong-process'), [])
        self.assertEqual(u.get_instances(self.c1, 'nn'),
                         self.ng1.instances)
        instances = list(self.ng2.instances)
        instances += self.ng3.instances
        self.assertEqual(u.get_instances(self.c1, 'dn'), instances)

    def test_get_instance(self):
        self.assertIsNone(u.get_instance(self.c1, 'wrong-process'))
        self.assertEqual(u.get_instance(self.c1, 'nn'),
                         self.ng1.instances[0])
        with testtools.ExpectedException(ex.InvalidComponentCountException):
            u.get_instance(self.c1, 'dn')

    def test_generate_lines_from_list(self):
        self.assertEqual(u.generate_host_names(self.ng2.instances),
                         "worker1\nworker2\nworker3")
        self.assertEqual(u.generate_host_names([]), "")


class GetPortUtilsTest(testtools.TestCase):
    def setUp(self):
        super(GetPortUtilsTest, self).setUp()
        self.test_values = [
            ('127.0.0.1:11000', 11000),
            ('http://somehost.com:8080/resource', 8080),
            ('http://192.168.1.101:10000', 10000),
            ('mydomain', None),
            ('domain:5000', 5000)
        ]

    def test_get_port_from_address(self):
        for address, port in self.test_values:
            self.assertEqual(u.get_port_from_address(address), port)
