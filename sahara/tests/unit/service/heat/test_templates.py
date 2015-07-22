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

from sahara.service.heat import templates as h
from sahara.tests.unit import base
from sahara.tests.unit import testutils as tu


class TestClusterTemplate(base.SaharaWithDbTestCase):
    """Checks valid structure of Resources section in generated Heat templates.

    1. It checks templates generation with different OpenStack
    network installations: Neutron, NovaNetwork with floating Ip auto
    assignment set to True or False.
    2. Cinder volume attachments.
    3. Basic instances creations with multi line user data provided.
    4. Anti-affinity feature with proper nova scheduler hints included
    into Heat templates.
    """

    def _make_node_groups(self, floating_ip_pool=None, volume_type=None):
        ng1 = tu.make_ng_dict('master', 42, ['namenode'], 1,
                              floating_ip_pool=floating_ip_pool, image_id=None,
                              volumes_per_node=0, volumes_size=0, id="1",
                              image_username='root', volume_type=None)
        ng2 = tu.make_ng_dict('worker', 42, ['datanode'], 1,
                              floating_ip_pool=floating_ip_pool, image_id=None,
                              volumes_per_node=2, volumes_size=10, id="2",
                              image_username='root', volume_type=volume_type)
        return ng1, ng2

    def _make_cluster(self, mng_network, ng1, ng2, anti_affinity=[]):
        return tu.create_cluster("cluster", "tenant1", "general",
                                 "1.2.1", [ng1, ng2],
                                 user_keypair_id='user_key',
                                 neutron_management_network=mng_network,
                                 default_image_id='1', image_id=None,
                                 anti_affinity=anti_affinity)

    def _make_heat_template(self, cluster, ng1, ng2):
        heat_template = h.ClusterStack(cluster)
        heat_template.add_node_group_extra(ng1['id'], 1,
                                           get_ud_generator('line1\nline2'))
        heat_template.add_node_group_extra(ng2['id'], 1,
                                           get_ud_generator('line2\nline3'))
        return heat_template

    def test_get_anti_affinity_scheduler_hints(self):
        ng1, ng2 = self._make_node_groups('floating')
        cluster = self._make_cluster('private_net', ng1, ng2,
                                     anti_affinity=["datanode"])
        heat_template = self._make_heat_template(cluster, ng1, ng2)

        ng1 = [ng for ng in cluster.node_groups if ng.name == "master"][0]
        ng2 = [ng for ng in cluster.node_groups if ng.name == "worker"][0]

        expected = {"scheduler_hints": {"group": {"Ref": "cluster-aa-group"}}}
        actual = heat_template._get_anti_affinity_scheduler_hints(ng2)
        self.assertEqual(expected, actual)

        expected = {}
        actual = heat_template._get_anti_affinity_scheduler_hints(ng1)
        self.assertEqual(expected, actual)

    def test_get_security_groups(self):
        ng1, ng2 = self._make_node_groups('floating')
        ng1['security_groups'] = ['1', '2']
        ng2['security_groups'] = ['3', '4']
        ng2['auto_security_group'] = True
        cluster = self._make_cluster('private_net', ng1, ng2)
        heat_template = self._make_heat_template(cluster, ng1, ng2)

        ng1 = [ng for ng in cluster.node_groups if ng.name == "master"][0]
        ng2 = [ng for ng in cluster.node_groups if ng.name == "worker"][0]

        expected = ['1', '2']
        actual = heat_template._get_security_groups(ng1)
        self.assertEqual(expected, actual)

        expected = ['3', '4', {'Ref': 'cluster-worker-2'}]
        actual = heat_template._get_security_groups(ng2)
        self.assertEqual(expected, actual)


def get_ud_generator(s):
    def generator(*args, **kwargs):
        return s
    return generator
