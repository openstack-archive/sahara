# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import testtools

import sahara.exceptions as e
from sahara.plugins.mapr.domain import node_process as np
from sahara.plugins.mapr.services.management import management
from sahara.plugins.mapr.services.maprfs import maprfs
from sahara.plugins.mapr.services.oozie import oozie
from sahara.plugins.mapr.services.swift import swift
from sahara.plugins.mapr.services.yarn import yarn
import sahara.plugins.mapr.versions.v5_0_0_mrv2.context as cc
import sahara.plugins.mapr.versions.v5_0_0_mrv2.version_handler as handler
from sahara.plugins import provisioning as p
from sahara.tests.unit import base as b
from sahara.tests.unit import testutils as tu


MANAGEMENT_IP = '1.1.1.1'
INTERNAL_IP = '1.1.1.2'


class TestClusterContext(b.SaharaTestCase):
    def __init__(self, *args, **kwds):
        super(TestClusterContext, self).__init__(*args, **kwds)
        self.fake_np = np.NodeProcess('fake', 'foo', 'bar')

    def _get_context(self):
        i1 = tu.make_inst_dict('id_1', 'instance_1', MANAGEMENT_IP)
        i1['internal_ip'] = INTERNAL_IP
        master_proc = [
            yarn.RESOURCE_MANAGER.ui_name,
            yarn.NODE_MANAGER.ui_name,
            yarn.HISTORY_SERVER.ui_name,
            maprfs.CLDB.ui_name,
            maprfs.FILE_SERVER.ui_name,
            oozie.OOZIE.ui_name,
            management.ZOOKEEPER.ui_name,
        ]
        master_ng = tu.make_ng_dict('master', 'large', master_proc, 1, [i1])
        cluster_configs = {
            'Service': {
                'key': 'value',
                'Service Version': '1.1',
            },
            'Oozie': {
                'Oozie Version': '4.1.0',
            }
        }
        cluster = tu.create_cluster(
            name='test_cluster',
            tenant='large',
            plugin='mapr',
            version='5.0.0.mrv2',
            node_groups=[master_ng],
            cluster_configs=cluster_configs,
        )
        self.ng = cluster.node_groups[0]
        self.instance = self.ng.instances[0]
        return cc.Context(cluster, handler.VersionHandler())

    def test_get_oozie_server_uri(self):
        ctx = self._get_context()
        expected = 'http://%s:11000/oozie' % MANAGEMENT_IP
        self.assertEqual(expected, ctx.oozie_server_uri)

    def test_oozie_server(self):
        ctx = self._get_context()
        node_processes = ctx.oozie_server.node_group.node_processes
        self.assertIn(oozie.OOZIE.ui_name, node_processes)

    def test_oozie_http(self):
        ctx = self._get_context()
        expected = '%s:11000' % MANAGEMENT_IP
        self.assertEqual(expected, ctx.oozie_http)

    def test_configure_sh(self):
        ctx = self._get_context()
        conf_sh = ctx.configure_sh
        pattern = (r'^(\S+)\s+(-N (\S+))\s+(-C (\S+))\s+(-Z (\S+))\s+'
                   r'(-no-autostart)\s+(-f)\s+\s(-HS (\S+))')
        self.assertRegex(conf_sh, pattern)
        self.assertIn('/opt/mapr/server/configure.sh', conf_sh)
        self.assertIn('-C %s' % INTERNAL_IP, conf_sh)
        self.assertIn('-Z %s' % INTERNAL_IP, conf_sh)
        self.assertIn('-HS %s' % INTERNAL_IP, conf_sh)
        self.assertIn('-no-autostart', conf_sh)
        self.assertIn('-N ' + ctx.cluster.name, conf_sh)

    def test_get_cluster_config_value(self):
        ctx = self._get_context()
        conf = p.Config('key', 'Service', 'cluster')
        self.assertEqual('value', ctx._get_cluster_config_value(conf))
        not_set = p.Config('nonset', 'Service', 'cluster')
        self.assertIsNone(ctx._get_cluster_config_value(not_set))

    def test_get_instances(self):
        ctx = self._get_context()
        instances = ctx.get_instances()
        self.assertEqual(1, len(instances))
        rms1 = ctx.get_instances(yarn.RESOURCE_MANAGER)
        self.assertEqual(1, len(rms1))
        rms2 = ctx.get_instances(yarn.RESOURCE_MANAGER.ui_name)
        self.assertEqual(1, len(rms2))
        not_existing_1 = ctx.get_instances(self.fake_np)
        self.assertEqual(0, len(not_existing_1))
        not_existing_2 = ctx.get_instances(self.fake_np.ui_name)
        self.assertEqual(0, len(not_existing_2))

    def test_get_instance(self):
        ctx = self._get_context()
        instance_1 = ctx.get_instance(yarn.RESOURCE_MANAGER)
        self.assertIn(yarn.RESOURCE_MANAGER.ui_name,
                      instance_1.node_group.node_processes)
        instance_2 = ctx.get_instance(yarn.RESOURCE_MANAGER)
        self.assertIn(yarn.RESOURCE_MANAGER.ui_name,
                      instance_2.node_group.node_processes)
        self.assertIsNone(ctx.get_instance(self.fake_np))

    def test_get_instances_ip(self):
        ctx = self._get_context()
        ip_list_1 = ctx.get_instances_ip(yarn.RESOURCE_MANAGER)
        self.assertEqual(1, len(ip_list_1))
        self.assertIn(INTERNAL_IP, ip_list_1)
        ip_list_2 = ctx.get_instances_ip(yarn.RESOURCE_MANAGER.ui_name)
        self.assertEqual(1, len(ip_list_2))
        self.assertIn(INTERNAL_IP, ip_list_2)
        empty_list = ctx.get_instances_ip(self.fake_np)
        self.assertEqual(0, len(empty_list))

    def test_get_instance_ip(self):
        ctx = self._get_context()
        ip_1 = ctx.get_instance_ip(yarn.RESOURCE_MANAGER)
        self.assertEqual(INTERNAL_IP, ip_1)
        ip_2 = ctx.get_instance_ip(yarn.RESOURCE_MANAGER.ui_name)
        self.assertEqual(INTERNAL_IP, ip_2)
        none_ip = ctx.get_instance_ip(self.fake_np)
        self.assertIsNone(none_ip)

    def test_get_zookeeper_nodes_ip_with_port(self):
        ctx = self._get_context()

        expected = '%s:5181' % INTERNAL_IP
        actual = ctx.get_zookeeper_nodes_ip_with_port()
        self.assertEqual(expected, actual)

        management.ZK_CLIENT_PORT = '0000'
        expected = '%s:0000' % INTERNAL_IP
        actual = ctx.get_zookeeper_nodes_ip_with_port()
        self.assertEqual(expected, actual)

    def test_filter_instances(self):
        ctx = self._get_context()
        instances = ctx.get_instances()
        rsmngs = ctx.filter_instances(instances, yarn.RESOURCE_MANAGER)
        self.assertEqual(1, len(rsmngs))
        not_existing_i = ctx.filter_instances(instances, self.fake_np)
        self.assertEqual(0, len(not_existing_i))

    def test_check_for_process(self):
        ctx = self._get_context()
        instance = ctx.get_instance(yarn.RESOURCE_MANAGER)
        self.assertTrue(ctx.check_for_process(instance, yarn.RESOURCE_MANAGER))
        self.assertTrue(ctx.check_for_process(instance,
                                              yarn.RESOURCE_MANAGER.ui_name))
        self.assertFalse(ctx.check_for_process(instance, maprfs.NFS))
        self.assertFalse(ctx.check_for_process(instance, maprfs.NFS.ui_name))

    def test_get_chosen_service_version(self):
        ctx = self._get_context()
        version = ctx.get_chosen_service_version('Service')
        self.assertEqual('1.1', version)

    def test_get_cluster_services(self):
        pass
        ctx = self._get_context()
        actual_services = ctx.get_cluster_services()
        actual_services_names = map(lambda s: s.ui_name, actual_services)
        expected_services_names = [
            yarn.YARN().ui_name,
            management.Management().ui_name,
            maprfs.MapRFS().ui_name,
            oozie.Oozie().ui_name,
            swift.Swift().ui_name,
        ]
        self.assertListEqual(sorted(actual_services_names),
                             sorted(expected_services_names))

    def test_get_service(self):
        ctx = self._get_context()
        service = ctx.get_service(yarn.HISTORY_SERVER)
        self.assertEqual(yarn.YARN().ui_name, service.ui_name)
        with testtools.ExpectedException(e.InvalidDataException):
            ctx.get_service(self.fake_np)

    def test_get_service_name_by_node_process(self):
        ctx = self._get_context()
        s_name_1 = ctx.get_service_name_by_node_process(yarn.RESOURCE_MANAGER)
        self.assertEqual(yarn.YARN().ui_name, s_name_1)
        s_name_2 = ctx.get_service_name_by_node_process(
            yarn.RESOURCE_MANAGER.ui_name)
        self.assertEqual(yarn.YARN().ui_name, s_name_2)
        not_existing_np = np.NodeProcess('not_existing', 'NotExisting', 'foo')
        self.assertIsNone(ctx.get_service_name_by_node_process(
            not_existing_np))
        self.assertIsNone(ctx.get_service_name_by_node_process(
            not_existing_np.ui_name))

    def test_get_instances_count(self):
        ctx = self._get_context()
        self.assertEqual(1, ctx.get_instances_count())
        self.assertEqual(1, ctx.get_instances_count(yarn.RESOURCE_MANAGER))
        self.assertEqual(1, ctx.get_instances_count(
            yarn.RESOURCE_MANAGER.ui_name))
        self.assertEqual(0, ctx.get_instances_count(self.fake_np))
        self.assertEqual(0, ctx.get_instances_count(
            self.fake_np.ui_name))

    def test_get_node_groups(self):
        ctx = self._get_context()
        all_ngs = ctx.get_node_groups()
        self.assertEqual(1, len(all_ngs))
        self.assertEqual([self.ng], all_ngs)
        rm_ngs_1 = ctx.get_node_groups(yarn.RESOURCE_MANAGER)
        self.assertEqual(1, len(rm_ngs_1))
        self.assertEqual([self.ng], rm_ngs_1)
        rm_ngs_2 = ctx.get_node_groups(yarn.RESOURCE_MANAGER.ui_name)
        self.assertEqual(1, len(rm_ngs_2))
        self.assertEqual([self.ng], rm_ngs_2)
        empty_ngs = ctx.get_node_groups(self.fake_np)
        self.assertEqual(0, len(empty_ngs))

    def test_get_cldb_nodes_ip(self):
        ctx = self._get_context()
        cldb_list_1 = ctx.get_cldb_nodes_ip()
        self.assertEqual(1, len(cldb_list_1.split(',')))
        self.assertIn(INTERNAL_IP, cldb_list_1)
        cldb_list_2 = ctx.get_cldb_nodes_ip()
        self.assertEqual(1, len(cldb_list_2.split(',')))
        self.assertIn(INTERNAL_IP, cldb_list_2)
        sep = ':'
        cldb_list_3 = ctx.get_cldb_nodes_ip(sep)
        self.assertEqual(1, len(cldb_list_3.split(sep)))
        self.assertIn(INTERNAL_IP, cldb_list_3)

    def test_get_zookeeper_nodes_ip(self):
        ctx = self._get_context()
        zk_list_1 = ctx.get_zookeeper_nodes_ip()
        self.assertEqual(1, len(zk_list_1.split(',')))
        self.assertIn(INTERNAL_IP, zk_list_1)
        zk_list_2 = ctx.get_zookeeper_nodes_ip()
        self.assertEqual(1, len(zk_list_2.split(',')))
        self.assertIn(INTERNAL_IP, zk_list_2)
        sep = ':'
        zk_list_3 = ctx.get_zookeeper_nodes_ip(sep)
        self.assertEqual(1, len(zk_list_3.split(sep)))
        self.assertIn(INTERNAL_IP, zk_list_3)

    def test_get_resourcemanager_ip(self):
        ctx = self._get_context()
        ip = ctx.get_resourcemanager_ip()
        self.assertEqual(INTERNAL_IP, ip)

    def test_get_historyserver_ip(self):
        ctx = self._get_context()
        self.assertTrue(ctx.has_control_nodes([self.instance]))

    def test_is_present(self):
        cluster_context = self._get_context()

        self.assertTrue(cluster_context.is_present(oozie.Oozie()))
        self.assertFalse(cluster_context.is_present(oozie.OozieV401()))
        self.assertTrue(cluster_context.is_present(oozie.OozieV410()))
