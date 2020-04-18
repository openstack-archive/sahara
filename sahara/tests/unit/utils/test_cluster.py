# Copyright (c) 2015 Intel Inc.
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

from sahara import conductor
from sahara import context
from sahara.tests.unit import base
from sahara.tests.unit.conductor import test_api
from sahara.utils import cluster as cluster_utils


class UtilsClusterTest(base.SaharaWithDbTestCase):
    def setUp(self):
        super(UtilsClusterTest, self).setUp()
        self.api = conductor.API

    def _make_sample(self):
        ctx = context.ctx()
        cluster = self.api.cluster_create(ctx, test_api.SAMPLE_CLUSTER)
        return cluster

    def test_change_cluster_status(self):
        cluster = self._make_sample()
        cluster = cluster_utils.change_cluster_status(
            cluster, cluster_utils.CLUSTER_STATUS_DELETING, "desc")
        self.assertEqual(cluster_utils.CLUSTER_STATUS_DELETING, cluster.status)
        self.assertEqual("desc", cluster.status_description)
        cluster_utils.change_cluster_status(
            cluster, cluster_utils.CLUSTER_STATUS_SPAWNING)
        self.assertEqual(cluster_utils.CLUSTER_STATUS_DELETING, cluster.status)

    def test_change_status_description(self):
        ctx = context.ctx()
        cluster = self._make_sample()
        cluster_id = cluster.id
        cluster = cluster_utils.change_cluster_status_description(
            cluster, "desc")
        self.assertEqual('desc', cluster.status_description)
        self.api.cluster_destroy(ctx, cluster)
        cluster = cluster_utils.change_cluster_status_description(
            cluster_id, "desc")
        self.assertIsNone(cluster)

    def test_count_instances(self):
        cluster = self._make_sample()
        self.assertEqual(4, cluster_utils.count_instances(cluster))

    def test_check_cluster_exists(self):
        ctx = context.ctx()
        cluster = self._make_sample()
        self.assertTrue(cluster_utils.check_cluster_exists(cluster))
        self.api.cluster_destroy(ctx, cluster)
        self.assertFalse(cluster_utils.check_cluster_exists(cluster))

    def test_get_instances(self):
        cluster = self._make_sample()
        ctx = context.ctx()
        idx = 0
        ids = []
        for ng in cluster.node_groups:
            for i in range(ng.count):
                idx += 1
                ids.append(self.api.instance_add(ctx, ng, {
                    'instance_id': str(idx),
                    'instance_name': str(idx),
                }))
        cluster = self.api.cluster_get(ctx, cluster)
        instances = cluster_utils.get_instances(cluster, ids)
        ids = set()
        for inst in instances:
            ids.add(inst.instance_id)
        self.assertEqual(idx, len(ids))
        for i in range(1, idx):
            self.assertIn(str(i), ids)

        instances = cluster_utils.get_instances(cluster)
        ids = set()
        for inst in instances:
            ids.add(inst.instance_id)
        self.assertEqual(idx, len(ids))
        for i in range(1, idx):
            self.assertIn(str(i), ids)

    def test_clean_cluster_from_empty_ng(self):
        ctx = context.ctx()
        cluster = self._make_sample()
        ng = cluster.node_groups[0]
        ng_len = len(cluster.node_groups)
        self.api.node_group_update(ctx, ng, {'count': 0})
        cluster = self.api.cluster_get(ctx, cluster.id)
        cluster_utils.clean_cluster_from_empty_ng(cluster)
        cluster = self.api.cluster_get(ctx, cluster.id)
        self.assertEqual(ng_len - 1, len(cluster.node_groups))

    @mock.patch("sahara.conductor.objects.Cluster.use_designate_feature")
    @mock.patch("socket.gethostbyname")
    @mock.patch("sahara.utils.openstack.base.url_for")
    def test_generate_etc_hosts(self, mock_url, mock_get_host,
                                mock_use_designate):
        cluster = self._make_sample()
        mock_use_designate.return_value = False
        ctx = context.ctx()
        idx = 0
        for ng in cluster.node_groups:
            for i in range(ng.count):
                idx += 1
                self.api.instance_add(ctx, ng, {
                    'instance_id': str(idx),
                    'instance_name': str(idx),
                    'internal_ip': str(idx),
                })
        cluster = self.api.cluster_get(ctx, cluster)

        mock_url.side_effect = ["http://keystone.local:1234/v13",
                                "http://swift.local:5678/v42"]
        mock_get_host.side_effect = ["1.2.3.4", "5.6.7.8"]

        value = cluster_utils.generate_etc_hosts(cluster)

        expected = ("127.0.0.1 localhost\n"
                    "1 1.novalocal 1\n"
                    "2 2.novalocal 2\n"
                    "3 3.novalocal 3\n"
                    "4 4.novalocal 4\n"
                    "1.2.3.4 keystone.local\n"
                    "5.6.7.8 swift.local\n")
        self.assertEqual(expected, value)

    @mock.patch("sahara.conductor.objects.Cluster.use_designate_feature")
    @mock.patch("socket.gethostbyname")
    @mock.patch("sahara.utils.openstack.base.url_for")
    def test_generate_etc_hosts_with_designate(self, mock_url, mock_get_host,
                                               mock_use_designate):
        cluster = self._make_sample()
        mock_use_designate.return_value = True
        mock_url.side_effect = ["http://keystone.local:1234/v13",
                                "http://swift.local:5678/v42"]
        mock_get_host.side_effect = ["1.2.3.4", "5.6.7.8"]

        value = cluster_utils.generate_etc_hosts(cluster)

        expected = ("127.0.0.1 localhost\n"
                    "1.2.3.4 keystone.local\n"
                    "5.6.7.8 swift.local\n")
        self.assertEqual(expected, value)

    def test_generate_resolv_conf_diff(self):
        curr_resolv_conf = "search openstacklocal\nnameserver 8.8.8.8\n"

        self.override_config("nameservers", ['1.1.1.1'])
        value = cluster_utils.generate_resolv_conf_diff(curr_resolv_conf)
        expected = "nameserver 1.1.1.1\n"
        self.assertEqual(expected, value)

        self.override_config("nameservers", ['1.1.1.1', '8.8.8.8', '2.2.2.2'])
        value = cluster_utils.generate_resolv_conf_diff(curr_resolv_conf)
        expected = ("nameserver 1.1.1.1\n"
                    "nameserver 2.2.2.2\n")
        self.assertEqual(expected, value)

    @mock.patch("socket.gethostbyname")
    @mock.patch("sahara.utils.openstack.base.url_for")
    def test_etc_hosts_entry_for_service_overrides(self, mock_url,
                                                   mock_get_host):
        self.override_config("object_store_ip_accessible", None)
        mock_url.return_value = "http://swift.org"
        mock_get_host.return_value = '1.1.1.1'

        res = cluster_utils.etc_hosts_entry_for_service('object-store')
        self.assertEqual('1.1.1.1 swift.org\n', res)

        self.override_config("object_store_ip_accessible", '2.2.2.2')

        res = cluster_utils.etc_hosts_entry_for_service('object-store')
        self.assertEqual('2.2.2.2 swift.org\n', res)
