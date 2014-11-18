# Copyright (c) 2014, MapR Technologies
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import os

import mock as m
import six

import sahara.plugins.mapr.util.config_file_utils as cfu
import sahara.plugins.mapr.util.plugin_spec as ps
import sahara.plugins.mapr.versions.v4_0_1_mrv1.cluster_configurer as bcc
import sahara.tests.unit.base as b
import sahara.tests.unit.plugins.mapr.stubs as s
import sahara.utils.files as f


__dirname__ = os.path.dirname(__file__)


class BaseClusterConfigurerTest(b.SaharaTestCase):

    def assertItemsEqual(self, expected, actual):
        for e in expected:
            self.assertIn(e, actual)
        for a in actual:
            self.assertIn(a, expected)

    @m.patch('sahara.utils.openstack.base.url_for')
    @m.patch('sahara.context.ctx')
    @m.patch('sahara.plugins.mapr.util.config.is_data_locality_enabled')
    @m.patch('sahara.plugins.mapr.util.config_file_utils.to_file_content')
    def test_configure_wo_generals(self, tfc_mock, gtm_mock, cc_mock,
                                   url_for_mock):
        def to_file_content(*args, **kargs):
            data = args[0]
            if isinstance(data, dict):
                return dict(map(lambda i: (str(i[0]), str(i[1])),
                                six.iteritems(args[0])))
            elif isinstance(data, str):
                return {None: data}
        tfc_mock.side_effect = to_file_content
        gtm_mock.return_value = False
        url_for_mock.return_value = 'http://auth'
        cc_mock.return_value = s.AttrDict(tenant_name='tenant_0',
                                          tenant_id='tenant_id',
                                          service_catalog=None)

        i0 = s.Instance(instance_name='i0',
                        management_ip='192.168.1.10',
                        internal_ip='10.10.1.10')
        i1 = s.Instance(instance_name='i1',
                        management_ip='192.168.1.11',
                        internal_ip='10.10.1.11')
        i2 = s.Instance(instance_name='i2',
                        management_ip='192.168.1.12',
                        internal_ip='10.10.1.12')
        np0 = ['ZooKeeper', 'FileServer', 'TaskTracker']
        np1 = ['ZooKeeper', 'NFS', 'Oozie']
        ng0 = s.NodeGroup(id='ng0', instances=[i0, i1], node_processes=np0)
        ng1 = s.NodeGroup(id='ng1', instances=[i2], node_processes=np1)
        cc = {'general': {}}
        cluster = s.Cluster(node_groups=[ng0, ng1], cluster_configs=cc,
                            hadoop_version='4.0.1.mrv1')

        plugin_spec = ps.PluginSpec(
            'tests/unit/plugins/mapr/utils/resources/plugin_spec_ci.json')
        configurer = bcc.ClusterConfigurer(cluster, plugin_spec)
        cu_mock = m.MagicMock()
        configurer.conductor = m.MagicMock()
        configurer.conductor.cluster_update = cu_mock
        configurer.configure()
        bcc_expected_path = (
            'tests/unit/plugins/mapr/utils/resources/bcc_expected')
        core_site = {'data': cfu.load_xml_file(('%s/core-site-0.xml'
                                                % bcc_expected_path)),
                     'file': ('/opt/mapr/hadoop/hadoop-0.20.2'
                              '/conf/core-site.xml'),
                     'root': True,
                     'timeout': 120}
        mapred_site = {'data': cfu.load_xml_file(('%s/mapred-site-0.xml'
                                                  % bcc_expected_path)),
                       'root': True,
                       'file': ('/opt/mapr/hadoop/hadoop-0.20.2'
                                '/conf/mapred-site.xml'),
                       'timeout': 120}
        cldb = {'root': True,
                'data': {'cldb.zookeeper.servers': ('192.168.1.10:5181,'
                                                    '192.168.1.11:5181,'
                                                    '192.168.1.12:5181')},
                'timeout': 120,
                'file': '/opt/mapr/conf/cldb.conf'}
        hadoop_v = {'root': True,
                    'data': f.get_file_text('plugins/mapr/util'
                                            '/resources/'
                                            'hadoop_version') %
                    {"mode": 'classic'},
                    'timeout': 120,
                    'file': '/opt/mapr/conf/hadoop_version'}
        self.assertItemsEqual(i0.remote().fs, [core_site, cldb, mapred_site,
                                               hadoop_v])
        self.assertItemsEqual(i1.remote().fs, [core_site, mapred_site, cldb,
                                               hadoop_v])
        self.assertItemsEqual(i2.remote().fs, [core_site, cldb,
                                               hadoop_v])

    @m.patch('sahara.utils.openstack.base.url_for')
    @m.patch('sahara.context.ctx')
    @m.patch('sahara.plugins.mapr.util.config.is_data_locality_enabled')
    @m.patch('sahara.topology.topology_helper.generate_topology_map')
    @m.patch('sahara.plugins.mapr.util.config_file_utils.to_file_content')
    def test_configure_with_topology(self, tfc_mock, gtm_mock,
                                     dle_mock, cc_mock, url_for_mock):
        def to_file_content(*args, **kargs):
            data = args[0]
            if isinstance(data, dict):
                return dict(map(lambda i: (str(i[0]), str(i[1])),
                                six.iteritems(args[0])))
            elif isinstance(data, str):
                return {None: data}
        tfc_mock.side_effect = to_file_content
        dle_mock.return_value = True
        gtm_mock.return_value = {'i0': 'r', '192.168.1.10': 'r',
                                 '10.10.1.10': 'r',
                                 'i1': 'r', '192.168.1.11': 'r',
                                 '10.10.1.11': 'r',
                                 'i2': 'r', '192.168.1.12': 'r',
                                 '10.10.1.12': 'r'}
        url_for_mock.return_value = 'http://auth'
        cc_mock.return_value = s.AttrDict(tenant_name='tenant_0',
                                          tenant_id='tenant_id',
                                          service_catalog=None)

        i0 = s.Instance(instance_name='i0',
                        management_ip='192.168.1.10',
                        internal_ip='10.10.1.10')
        i1 = s.Instance(instance_name='i1',
                        management_ip='192.168.1.11',
                        internal_ip='10.10.1.11')
        i2 = s.Instance(instance_name='i2',
                        management_ip='192.168.1.12',
                        internal_ip='10.10.1.12')
        np0 = ['ZooKeeper', 'FileServer', 'TaskTracker']
        np1 = ['ZooKeeper', 'NFS', 'HBase RegionServer']
        ng0 = s.NodeGroup(id='ng0', instances=[i0, i1], node_processes=np0)
        ng1 = s.NodeGroup(id='ng1', instances=[i2], node_processes=np1)
        cc = {'general': {}}
        cluster = s.Cluster(node_groups=[ng0, ng1], cluster_configs=cc,
                            hadoop_version='4.0.1.mrv1')
        plugin_spec = ps.PluginSpec(
            'tests/unit/plugins/mapr/utils/resources/plugin_spec_ci.json')
        configurer = bcc.ClusterConfigurer(cluster, plugin_spec)
        cu_mock = m.MagicMock()
        configurer.conductor = m.MagicMock()
        configurer.conductor.cluster_update = cu_mock
        configurer.configure()
        self.assertEqual(1, gtm_mock.call_count)
        bcc_expected_path = (
            'tests/unit/plugins/mapr/utils/resources/bcc_expected')
        core_site = {'data': cfu.load_xml_file(('%s/core-site-1.xml'
                                                % bcc_expected_path)),
                     'file': ('/opt/mapr/hadoop/hadoop-0.20.2'
                              '/conf/core-site.xml'),
                     'root': True,
                     'timeout': 120}
        mapred_site = {'data': cfu.load_xml_file('%s/mapred-site-1.xml'
                                                 % bcc_expected_path),
                       'root': True,
                       'file': ('/opt/mapr/hadoop/hadoop-0.20.2'
                                '/conf/mapred-site.xml'),
                       'timeout': 120}
        topology_data = {'data': gtm_mock.return_value,
                         'file': '/opt/mapr/topology.data',
                         'root': True, 'timeout': 120}
        cldb = {'data': cfu.load_properties_file(('%s/cldb-1.conf'
                                                  % bcc_expected_path)),
                'file': '/opt/mapr/conf/cldb.conf',
                'root': True, 'timeout': 120}
        t_sh = {'data': f.get_file_text('plugins/mapr/util'
                                        '/resources/topology.sh'),
                'file': '/opt/mapr/topology.sh',
                'root': True, 'timeout': 120}
        hadoop_v = {'root': True,
                    'data': f.get_file_text('plugins/mapr/util'
                                            '/resources/hadoop_version') %
                    {'mode': 'classic'},
                    'timeout': 120,
                    'file': '/opt/mapr/conf/hadoop_version'}
        self.assertItemsEqual(i0.remote().fs,
                              [core_site, mapred_site,
                               topology_data, cldb, t_sh, hadoop_v])
        self.assertItemsEqual(i1.remote().fs,
                              [core_site, mapred_site,
                               topology_data, cldb, t_sh, hadoop_v])
        self.assertItemsEqual(i2.remote().fs,
                              [core_site, topology_data, cldb, t_sh,
                               hadoop_v])
