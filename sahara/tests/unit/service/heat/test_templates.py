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

from unittest import mock

from sahara.conductor import resource as r
from sahara.service.heat import templates as h
from sahara.tests.unit import base
from sahara.tests.unit import testutils as tu


class BaseTestClusterTemplate(base.SaharaWithDbTestCase):
    """Checks valid structure of Resources section in generated Heat templates.

    1. It checks templates generation with OpenStack network
    installation: Neutron.
    2. Cinder volume attachments.
    3. Basic instances creations with multi line user data provided.
    4. Anti-affinity feature with proper nova scheduler hints included
    into Heat templates.
    """
    def _make_node_groups(self, floating_ip_pool=None, volume_type=None):
        ng1 = tu.make_ng_dict('master', 42, ['namenode'], 1,
                              floating_ip_pool=floating_ip_pool, image_id=None,
                              volumes_per_node=0, volumes_size=0, id="1",
                              image_username='root', volume_type=None,
                              boot_from_volume=False, auto_security_group=True)
        ng2 = tu.make_ng_dict('worker', 42, ['datanode'], 1,
                              floating_ip_pool=floating_ip_pool, image_id=None,
                              volumes_per_node=2, volumes_size=10, id="2",
                              image_username='root', volume_type=volume_type,
                              boot_from_volume=False, auto_security_group=True)
        return ng1, ng2

    def _make_cluster(self, mng_network, ng1, ng2, anti_affinity=None,
                      domain_name=None):
        return tu.create_cluster("cluster", "tenant1", "general",
                                 "2.6.0", [ng1, ng2],
                                 user_keypair_id='user_key',
                                 neutron_management_network=mng_network,
                                 default_image_id='1', image_id=None,
                                 anti_affinity=anti_affinity or [],
                                 domain_name=domain_name,
                                 anti_affinity_ratio=1)


class TestClusterTemplate(BaseTestClusterTemplate):
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

        expected = {
            "scheduler_hints": {
                "group": {
                    "get_param": [h.SERVER_GROUP_NAMES, {"get_param":
                                                         "instance_index"}]
                }
            }
        }

        actual = heat_template._get_anti_affinity_scheduler_hints(ng2)
        self.assertEqual(expected, actual)

        expected = {}
        actual = heat_template._get_anti_affinity_scheduler_hints(ng1)
        self.assertEqual(expected, actual)

    def test_get_security_groups(self):
        ng1, ng2 = self._make_node_groups('floating')
        ng1['security_groups'] = ['1', '2']
        ng1['auto_security_group'] = False
        ng2['security_groups'] = ['3', '4']
        ng2['auto_security_group'] = True
        cluster = self._make_cluster('private_net', ng1, ng2)
        heat_template = self._make_heat_template(cluster, ng1, ng2)

        ng1 = [ng for ng in cluster.node_groups if ng.name == "master"][0]
        ng2 = [ng for ng in cluster.node_groups if ng.name == "worker"][0]
        expected = ['1', '2']
        actual = heat_template._get_security_groups(ng1)
        self.assertEqual(expected, actual)

        expected = ['3', '4', {'get_param': 'autosecgroup'}]
        actual = heat_template._get_security_groups(ng2)
        self.assertEqual(expected, actual)

    def test_get_security_groups_empty(self):
        ng1, _ = self._make_node_groups()
        ng1['security_groups'] = None
        ng1['auto_security_group'] = False
        cluster = self._make_cluster('private_net', ng1, ng1)
        heat_template = self._make_heat_template(cluster, ng1, ng1)

        ng1 = [ng for ng in cluster.node_groups if ng.name == "master"][0]
        actual = heat_template._get_security_groups(ng1)
        self.assertEqual([], actual)

    def _generate_auto_security_group_template(self):
        ng1, ng2 = self._make_node_groups('floating')
        cluster = self._make_cluster('private_net', ng1, ng2)
        ng1['cluster'] = cluster
        ng2['cluster'] = cluster
        ng1 = r.NodeGroupResource(ng1)
        ng2 = r.NodeGroupResource(ng2)
        heat_template = self._make_heat_template(cluster, ng1, ng2)
        return heat_template._serialize_auto_security_group(ng1)

    @mock.patch('sahara.utils.openstack.neutron.get_private_network_cidrs')
    def test_serialize_auto_security_group_neutron(self, patched):
        ipv4_cidr = '192.168.0.0/24'
        ipv6_cidr = 'fe80::/64'
        patched.side_effect = lambda cluster: [ipv4_cidr, ipv6_cidr]
        expected_rules = [
            ('0.0.0.0/0', 'IPv4', 'tcp', '22', '22'),
            ('::/0', 'IPv6', 'tcp', '22', '22'),
            (ipv4_cidr, 'IPv4', 'tcp', '1', '65535'),
            (ipv4_cidr, 'IPv4', 'udp', '1', '65535'),
            (ipv4_cidr, 'IPv4', 'icmp', '0', '255'),
            (ipv6_cidr, 'IPv6', 'tcp', '1', '65535'),
            (ipv6_cidr, 'IPv6', 'udp', '1', '65535'),
            (ipv6_cidr, 'IPv6', 'icmp', '0', '255'),
        ]
        expected = {'cluster-master-1': {
            'type': 'OS::Neutron::SecurityGroup',
            'properties': {
                'description': 'Data Processing Cluster by Sahara\n'
                               'Sahara cluster name: cluster\n'
                               'Sahara engine: heat.3.0\n'
                               'Auto security group for Sahara Node '
                               'Group: master',
                'rules': [{
                    'remote_ip_prefix': rule[0],
                    'ethertype': rule[1],
                    'protocol': rule[2],
                    'port_range_min': rule[3],
                    'port_range_max': rule[4]
                } for rule in expected_rules]
            }
        }}
        actual = self._generate_auto_security_group_template()
        self.assertEqual(expected, actual)

    @mock.patch("sahara.conductor.objects.Cluster.use_designate_feature")
    def test_serialize_designate_records(self, mock_use_designate):
        ng1, ng2 = self._make_node_groups('floating')
        cluster = self._make_cluster('private_net', ng1, ng2,
                                     domain_name='domain.org.')

        mock_use_designate.return_value = False
        heat_template = self._make_heat_template(cluster, ng1, ng2)
        expected = {}
        actual = heat_template._serialize_designate_records()
        self.assertEqual(expected, actual)

        mock_use_designate.return_value = True
        heat_template = self._make_heat_template(cluster, ng1, ng2)
        expected = {
            'internal_designate_record': {
                'properties': {
                    'domain': 'domain.org.',
                    'name': {
                        'list_join': [
                            '.',
                            [{'get_attr': ['inst', 'name']}, 'domain.org.']]
                    },
                    'data': {'get_attr': ['inst', 'networks', 'private', 0]},
                    'type': 'A'
                },
                'type': 'OS::Designate::Record'
            },
            'external_designate_record': {
                'properties': {
                    'domain': 'domain.org.',
                    'name': {
                        'list_join': [
                            '.',
                            [{'get_attr': ['inst', 'name']}, 'domain.org.']]
                    },
                    'data': {'get_attr': ['floating_ip', 'ip']},
                    'type': 'A'
                },
                'type': 'OS::Designate::Record'
            }
        }
        actual = heat_template._serialize_designate_records()
        self.assertEqual(expected, actual)

    @mock.patch("sahara.conductor.objects.Cluster.use_designate_feature")
    def test_serialize_designate_reversed_records(self, mock_use_designate):

        def _generate_reversed_ip(ip):
            return {
                'list_join': [
                    '.',
                    [
                        {'str_split': ['.', ip, 3]},
                        {'str_split': ['.', ip, 2]},
                        {'str_split': ['.', ip, 1]},
                        {'str_split': ['.', ip, 0]},
                        'in-addr.arpa.'
                    ]
                ]
            }

        ng1, ng2 = self._make_node_groups('floating')
        cluster = self._make_cluster('private_net', ng1, ng2,
                                     domain_name='domain.org.')

        mock_use_designate.return_value = False
        heat_template = self._make_heat_template(cluster, ng1, ng2)
        expected = {}
        actual = heat_template._serialize_designate_reverse_records()
        self.assertEqual(expected, actual)

        mock_use_designate.return_value = True
        heat_template = self._make_heat_template(cluster, ng1, ng2)
        expected = {
            'internal_designate_reverse_record': {
                'properties': {
                    'domain': 'in-addr.arpa.',
                    'name': _generate_reversed_ip(
                        {'get_attr': ['inst', 'networks', 'private', 0]}),
                    'data': {
                        'list_join': [
                            '.',
                            [{'get_attr': ['inst', 'name']}, 'domain.org.']]
                    },
                    'type': 'PTR'
                },
                'type': 'OS::Designate::Record'
            },
            'external_designate_reverse_record': {
                'properties': {
                    'domain': 'in-addr.arpa.',
                    'name': _generate_reversed_ip(
                        {'get_attr': ['floating_ip', 'ip']}),
                    'data': {
                        'list_join': [
                            '.',
                            [{'get_attr': ['inst', 'name']}, 'domain.org.']]
                    },
                    'type': 'PTR'
                },
                'type': 'OS::Designate::Record'
            }
        }
        actual = heat_template._serialize_designate_reverse_records()
        self.assertEqual(expected, actual)


class TestClusterTemplateWaitCondition(BaseTestClusterTemplate):
    def _make_heat_template(self, cluster, ng1, ng2):
        heat_template = h.ClusterStack(cluster)
        heat_template.add_node_group_extra(ng1.id, 1,
                                           get_ud_generator('line1\nline2'))
        heat_template.add_node_group_extra(ng2.id, 1,
                                           get_ud_generator('line2\nline3'))
        return heat_template

    def setUp(self):
        super(TestClusterTemplateWaitCondition, self).setUp()
        _ng1, _ng2 = self._make_node_groups("floating")
        _cluster = self._make_cluster("private_net", _ng1, _ng2)
        _ng1["cluster"] = _ng2["cluster"] = _cluster
        self.ng1 = mock.Mock()
        self.ng1.configure_mock(**_ng1)
        self.ng2 = mock.Mock()
        self.ng2.configure_mock(**_ng2)
        self.cluster = mock.Mock()
        self.cluster.configure_mock(**_cluster)
        self.template = self._make_heat_template(self.cluster,
                                                 self.ng1, self.ng2)

    @mock.patch('sahara.utils.cluster.etc_hosts_entry_for_service')
    def test_use_wait_condition(self, etc_hosts):
        etc_hosts.return_value = "data"
        self.override_config('heat_enable_wait_condition', True)
        instance = self.template._serialize_instance(self.ng1)
        expected_wc_handle = {
            "type": "OS::Heat::WaitConditionHandle"
        }
        expected_wc_waiter = {
            "type": "OS::Heat::WaitCondition",
            "depends_on": "inst",
            "properties": {
                "timeout": 3600,
                "handle": {"get_resource": "master-wc-handle"}
            }
        }
        self.assertEqual(expected_wc_handle, instance["master-wc-handle"])
        self.assertEqual(expected_wc_waiter, instance["master-wc-waiter"])


def get_ud_generator(s):
    def generator(*args, **kwargs):
        return s
    return generator
