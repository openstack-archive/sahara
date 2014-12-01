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

import json

import mock
import testtools

from sahara import exceptions as ex
from sahara.tests.unit import base
from sahara.tests.unit import testutils as tu
from sahara.utils import files as f
from sahara.utils.openstack import heat as h


class TestHeat(testtools.TestCase):
    def test_gets(self):
        inst_name = "cluster-worker-001"
        self.assertEqual(h._get_inst_name("cluster", "worker", 0), inst_name)
        self.assertEqual(h._get_inst_name("CLUSTER", "WORKER", 0), inst_name)
        self.assertEqual(h._get_port_name(inst_name),
                         "cluster-worker-001-port")
        self.assertEqual(h._get_floating_name(inst_name),
                         "cluster-worker-001-floating")
        self.assertEqual(h._get_floating_assoc_name(inst_name),
                         "cluster-worker-001-floating-assoc")
        self.assertEqual(h._get_volume_name(inst_name, 1),
                         "cluster-worker-001-volume-1")
        self.assertEqual(h._get_volume_attach_name(inst_name, 1),
                         "cluster-worker-001-volume-attachment-1")

    def test_prepare_user_data(self):
        userdata = "line1\nline2"
        self.assertEqual(h._prepare_userdata(userdata), '"line1",\n"line2"')


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
                              volumes_per_node=0, volumes_size=0, id=1,
                              image_username='root', volume_type=None)
        ng2 = tu.make_ng_dict('worker', 42, ['datanode'], 1,
                              floating_ip_pool=floating_ip_pool, image_id=None,
                              volumes_per_node=2, volumes_size=10, id=2,
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
        heat_template = h.ClusterTemplate(cluster)
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

        expected = ('"scheduler_hints" : '
                    '{"group": {"Ref": "cluster-aa-group"}},')
        actual = heat_template._get_anti_affinity_scheduler_hints(ng2)
        self.assertEqual(expected, actual)

        expected = ''
        actual = heat_template._get_anti_affinity_scheduler_hints(ng1)
        self.assertEqual(expected, actual)

    def test_load_template_use_neutron(self):
        """Test for Heat cluster template with Neutron enabled.

        Two NodeGroups used: 'master' with Ephemeral drive attached and
        'worker' with 2 attached volumes 10GB size each
        """

        ng1, ng2 = self._make_node_groups('floating', 'vol_type')
        cluster = self._make_cluster('private_net', ng1, ng2)
        heat_template = self._make_heat_template(cluster, ng1, ng2)
        self.override_config("use_neutron", True)
        main_template = h._load_template(
            'main.heat', {'resources':
                          heat_template._serialize_resources()})

        self.assertEqual(
            json.loads(main_template),
            json.loads(f.get_file_text(
                "tests/unit/resources/"
                "test_serialize_resources_use_neutron.heat")))

    def test_load_template_use_nova_network_without_autoassignment(self):
        """Checks Heat cluster template with Nova Network enabled.

        Nova Network checked without autoassignment of floating ip.

        Two NodeGroups used: 'master' with Ephemeral drive attached and
        'worker' with 2 attached volumes 10GB size each
        """

        ng1, ng2 = self._make_node_groups('floating')
        cluster = self._make_cluster(None, ng1, ng2)
        heat_template = self._make_heat_template(cluster, ng1, ng2)
        self.override_config("use_neutron", False)
        main_template = h._load_template(
            'main.heat', {'resources':
                          heat_template._serialize_resources()})

        self.assertEqual(
            json.loads(main_template),
            json.loads(f.get_file_text(
                "tests/unit/resources/"
                "test_serialize_resources_use_nn_without_autoassignment.heat"))
        )

    def test_load_template_use_nova_network_with_autoassignment(self):
        """Checks Heat cluster template with Nova Network enabled.

        Nova Network checked with autoassignment of floating ip.

        Two NodeGroups used: 'master' with Ephemeral drive attached and
        'worker' with 2 attached volumes 10GB size each
        """

        ng1, ng2 = self._make_node_groups()
        cluster = self._make_cluster(None, ng1, ng2)
        heat_template = self._make_heat_template(cluster, ng1, ng2)
        self.override_config("use_neutron", False)
        main_template = h._load_template(
            'main.heat', {'resources':
                          heat_template._serialize_resources()})

        self.assertEqual(
            json.loads(main_template),
            json.loads(f.get_file_text(
                "tests/unit/resources/"
                "test_serialize_resources_use_nn_with_autoassignment.heat"))
        )

    def test_load_template_with_anti_affinity_single_ng(self):
        """Checks Heat cluster template with Neutron enabled.

        Checks also anti-affinity feature enabled for single node process
        in single node group.
        """

        ng1 = tu.make_ng_dict('master', 42, ['namenode'], 1,
                              floating_ip_pool='floating', image_id=None,
                              volumes_per_node=0, volumes_size=0, id=1,
                              image_username='root')
        ng2 = tu.make_ng_dict('worker', 42, ['datanode'], 2,
                              floating_ip_pool='floating', image_id=None,
                              volumes_per_node=0, volumes_size=0, id=2,
                              image_username='root')
        cluster = tu.create_cluster("cluster", "tenant1", "general",
                                    "1.2.1", [ng1, ng2],
                                    user_keypair_id='user_key',
                                    neutron_management_network='private_net',
                                    default_image_id='1',
                                    anti_affinity=['datanode'], image_id=None)
        aa_heat_template = h.ClusterTemplate(cluster)
        aa_heat_template.add_node_group_extra(ng1['id'], 1,
                                              get_ud_generator('line1\nline2'))
        aa_heat_template.add_node_group_extra(ng2['id'], 2,
                                              get_ud_generator('line2\nline3'))

        self.override_config("use_neutron", True)
        main_template = h._load_template(
            'main.heat', {'resources':
                          aa_heat_template._serialize_resources()})

        self.assertEqual(
            json.loads(main_template),
            json.loads(f.get_file_text(
                "tests/unit/resources/"
                "test_serialize_resources_aa.heat")))


class TestClusterStack(testtools.TestCase):
    @mock.patch("sahara.context.sleep", return_value=None)
    def test_wait_completion(self, _):
        stack = FakeHeatStack('CREATE_IN_PROGRESS', 'CREATE_COMPLETE')
        h.wait_stack_completion(stack)

        stack = FakeHeatStack('UPDATE_IN_PROGRESS', 'UPDATE_COMPLETE')
        h.wait_stack_completion(stack)

        stack = FakeHeatStack('DELETE_IN_PROGRESS', 'DELETE_COMPLETE')
        h.wait_stack_completion(stack)

        stack = FakeHeatStack('CREATE_IN_PROGRESS', 'CREATE_FAILED')
        with testtools.ExpectedException(
                ex.HeatStackException,
                value_re=("Heat stack failed with status "
                          "CREATE_FAILED\nError ID: .*")):
            h.wait_stack_completion(stack)


class FakeHeatStack(object):
    def __init__(self, stack_status=None, new_status=None, stack_name=None):
        self.stack_status = stack_status or ''
        self.new_status = new_status or ''
        self.stack_name = stack_name or ''

    def get(self):
        self.stack_status = self.new_status

    @property
    def status(self):
        s = self.stack_status
        return s[s.index('_') + 1:]


def get_ud_generator(s):
    def generator(*args, **kwargs):
        return s
    return generator
