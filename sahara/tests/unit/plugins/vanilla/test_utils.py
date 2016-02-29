# Copyright (c) 2014 Mirantis Inc.
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

from sahara.plugins.vanilla import plugin as p
from sahara.plugins.vanilla import utils as u
from sahara.tests.unit import base
from sahara.tests.unit import testutils as tu


class TestUtils(base.SaharaWithDbTestCase):

    def setUp(self):
        super(TestUtils, self).setUp()
        self.plugin = p.VanillaProvider()

        self.ng_manager = tu.make_ng_dict(
            'mng', 'f1', ['manager'], 1,
            [tu.make_inst_dict('mng1', 'manager')])
        self.ng_namenode = tu.make_ng_dict(
            'nn', 'f1', ['namenode'], 1,
            [tu.make_inst_dict('nn1', 'namenode')])
        self.ng_resourcemanager = tu.make_ng_dict(
            'jt', 'f1', ['resourcemanager'], 1,
            [tu.make_inst_dict('jt1', 'resourcemanager')])
        self.ng_datanode = tu.make_ng_dict(
            'dn', 'f1', ['datanode'], 2,
            [tu.make_inst_dict('dn1', 'datanode-1'),
             tu.make_inst_dict('dn2', 'datanode-2')])
        self.ng_nodemanager = tu.make_ng_dict(
            'tt', 'f1', ['nodemanager'], 2,
            [tu.make_inst_dict('tt1', 'nodemanager-1'),
             tu.make_inst_dict('tt2', 'nodemanager-2')])
        self.ng_oozie = tu.make_ng_dict(
            'ooz1', 'f1', ['oozie'], 1,
            [tu.make_inst_dict('ooz1', 'oozie')])
        self.ng_hiveserver = tu.make_ng_dict(
            'hs', 'f1', ['hiveserver'], 1,
            [tu.make_inst_dict('hs1', 'hiveserver')])
        self.ng_secondarynamenode = tu.make_ng_dict(
            'snn', 'f1', ['secondarynamenode'], 1,
            [tu.make_inst_dict('snn1', 'secondarynamenode')])

    def test_get_namenode(self):
        cl = tu.create_cluster('cl1', 't1', 'vanilla', '2.7.1',
                               [self.ng_manager, self.ng_namenode])
        self.assertEqual('nn1', u.get_namenode(cl).instance_id)

        cl = tu.create_cluster('cl1', 't1', 'vanilla', '2.7.1',
                               [self.ng_manager])
        self.assertIsNone(u.get_namenode(cl))

    def test_get_oozie(self):
        cl = tu.create_cluster('cl1', 't1', 'vanilla', '2.7.1',
                               [self.ng_manager, self.ng_oozie])
        self.assertEqual('ooz1', u.get_oozie(cl).instance_id)

        cl = tu.create_cluster('cl1', 't1', 'vanilla', '2.7.1',
                               [self.ng_manager])
        self.assertIsNone(u.get_oozie(cl))

    def test_get_hiveserver(self):
        cl = tu.create_cluster('cl1', 't1', 'vanilla', '2.7.1',
                               [self.ng_manager, self.ng_hiveserver])
        self.assertEqual('hs1', u.get_hiveserver(cl).instance_id)

        cl = tu.create_cluster('cl1', 't1', 'vanilla', '2.7.1',
                               [self.ng_manager])
        self.assertIsNone(u.get_hiveserver(cl))

    def test_get_datanodes(self):
        cl = tu.create_cluster('cl1', 't1', 'vanilla', '2.7.1',
                               [self.ng_manager, self.ng_namenode,
                                self.ng_datanode])
        datanodes = u.get_datanodes(cl)
        self.assertEqual(2, len(datanodes))
        self.assertEqual(set(['dn1', 'dn2']),
                         set([datanodes[0].instance_id,
                              datanodes[1].instance_id]))

        cl = tu.create_cluster('cl1', 't1', 'vanilla', '2.7.1',
                               [self.ng_manager])
        self.assertEqual([], u.get_datanodes(cl))

    def test_get_secondarynamenodes(self):
        cl = tu.create_cluster('cl1', 't1', 'vanilla', '2.7.1',
                               [self.ng_manager, self.ng_namenode,
                                self.ng_secondarynamenode])
        self.assertEqual('snn1', u.get_secondarynamenode(cl).instance_id)

        cl = tu.create_cluster('cl1', 't1', 'vanilla', '2.7.1',
                               [self.ng_manager])
        self.assertIsNone(u.get_secondarynamenode(cl))
