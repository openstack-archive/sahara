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

from sahara.plugins.cdh import plugin_utils as pu
from sahara.tests.unit import base
from sahara.tests.unit.plugins.cdh import utils as tu


PU = pu.AbstractPluginUtils()


class UtilsTestCase(base.SaharaTestCase):
    def test_get_manager(self):
        cluster = tu.get_fake_cluster()
        inst = PU.get_manager(cluster)
        self.assertEqual('id1', inst.instance_id)

    def test_get_namenode(self):
        cluster = tu.get_fake_cluster()
        inst = PU.get_namenode(cluster)
        self.assertEqual('id2', inst.instance_id)

    def test_get_secondarynamenode(self):
        cluster = tu.get_fake_cluster()
        inst = PU.get_secondarynamenode(cluster)
        self.assertEqual('id2', inst.instance_id)

    def test_get_resourcemanager(self):
        cluster = tu.get_fake_cluster()
        inst = PU.get_resourcemanager(cluster)
        self.assertEqual('id2', inst.instance_id)

    def test_get_datanodes(self):
        cluster = tu.get_fake_cluster()
        dns = PU.get_datanodes(cluster)
        ids = [dn.instance_id for dn in dns]
        self.assertEqual(sorted(['id00', 'id01', 'id02']), sorted(ids))

    def test_get_nodemanagers(self):
        cluster = tu.get_fake_cluster()
        nms = PU.get_nodemanagers(cluster)
        ids = [nm.instance_id for nm in nms]
        self.assertEqual(sorted(['id00', 'id01', 'id02']), sorted(ids))

    def test_get_historyserver(self):
        cluster = tu.get_fake_cluster()
        inst = PU.get_historyserver(cluster)
        self.assertEqual('id2', inst.instance_id)

    def test_get_oozie(self):
        cluster = tu.get_fake_cluster()
        inst = PU.get_oozie(cluster)
        self.assertEqual('id2', inst.instance_id)
