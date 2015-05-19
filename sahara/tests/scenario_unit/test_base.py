# Copyright (c) 2015 Mirantis Inc.
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

import mock
from saharaclient.api import cluster_templates
from saharaclient.api import clusters
from saharaclient.api import data_sources
from saharaclient.api import images
from saharaclient.api import job_binaries
from saharaclient.api import job_binary_internals
from saharaclient.api import job_executions
from saharaclient.api import jobs
from saharaclient.api import node_group_templates
from saharaclient.api import plugins
from tempest_lib import exceptions as exc
import testtools

from sahara.tests.scenario import base
from sahara.tests.scenario import timeouts


class FakeSaharaClient(object):
    def __init__(self):
        self.clusters = clusters.ClusterManager(None)
        self.cluster_templates = cluster_templates.ClusterTemplateManager(None)
        self.node_group_templates = (node_group_templates.
                                     NodeGroupTemplateManager(None))
        self.plugins = plugins.PluginManager(None)
        self.images = images.ImageManager(None)

        self.data_sources = data_sources.DataSourceManager(None)
        self.jobs = jobs.JobsManager(None)
        self.job_executions = job_executions.JobExecutionsManager(None)
        self.job_binaries = job_binaries.JobBinariesManager(None)
        self.job_binary_internals = (
            job_binary_internals.JobBinaryInternalsManager(None))


class FakeCluster(object):
    def __init__(self, is_transient, provision_progress):
        self.is_transient = is_transient
        self.provision_progress = provision_progress


class FakeResponse(object):
    def __init__(self, set_id=None, set_status=None):
        self.id = set_id
        self.status = set_status


class TestBase(testtools.TestCase):
    def setUp(self):
        super(TestBase, self).setUp()
        with mock.patch(
                'sahara.tests.scenario.base.BaseTestCase.__init__'
        ) as mock_init:
            mock_init.return_value = None
            self.base_scenario = base.BaseTestCase()
        self.base_scenario.credentials = {'os_username': 'admin',
                                          'os_password': 'nova',
                                          'os_tenant': 'admin',
                                          'os_auth_url':
                                              'http://localhost:5000/v2.0',
                                          'sahara_service_type':
                                              'data-processing-local',
                                          'sahara_url':
                                              'http://sahara_host:8386/v1.1'}
        self.base_scenario.plugin_opts = {'plugin_name': 'vanilla',
                                          'hadoop_version': '2.6.0'}
        self.base_scenario.network = {'type': 'neutron',
                                      'private_network': 'changed_private',
                                      'public_network': 'changed_public',
                                      'auto_assignment_floating_ip': False}
        self.base_scenario.testcase = {
            'node_group_templates': [
                {
                    'name': 'master',
                    'node_processes': ['namenode', 'oozie', 'resourcemanager'],
                    'flavor_id': '2'
                },
                {
                    'name': 'worker',
                    'node_processes': ['datanode', 'nodemanager'],
                    'flavor_id': '2'
                }],
            'cluster_template':
                {
                    'name': 'test_name_ct',
                    'node_group_templates':
                        {
                            'master': 1,
                            'worker': 3
                        }
                },
            'timeout_poll_cluster_status': 300,
            'timeout_delete_resource': 300,
            'timeout_poll_jobs_status': 2,
            'timeout_check_transient': 3,
            'retain_resources': True,
            'image': 'image_name',
            "edp_jobs_flow":
                {
                    "test_flow":
                        [{
                            "type": "Pig",
                            "input_datasource":
                                {
                                    "type": "swift",
                                    "source": "etc/edp-examples/edp-pig/"
                                              "top-todoers/data/input"
                                },
                            "output_datasource":
                                {
                                    "type": "hdfs",
                                    "destination": "/user/hadoop/edp-output"
                                },
                            "main_lib":
                                {
                                    "type": "swift",
                                    "source": "etc/edp-examples/edp-pig/"
                                              "top-todoers/example.pig"
                                }
                        }],
                },
        }
        self.base_scenario.ng_id_map = {'worker': 'set_id', 'master': 'set_id'}
        self.base_scenario.ng_name_map = {}
        self.base_scenario.template_path = ('sahara/tests/scenario/templates/'
                                            'vanilla/2.6.0')
        self.job = self.base_scenario.testcase["edp_jobs_flow"].get(
            'test_flow')[0]
        self.base_scenario.setUpClass()
        timeouts.Defaults.init_defaults(self.base_scenario.testcase)

    @mock.patch('keystoneclient.auth.identity.v3.Password')
    @mock.patch('keystoneclient.session.Session')
    @mock.patch('saharaclient.client.Client', return_value=None)
    @mock.patch('novaclient.client.Client', return_value=None)
    @mock.patch('neutronclient.neutron.client.Client', return_value=None)
    @mock.patch('swiftclient.client.Connection', return_value=None)
    def test__init_clients(self, swift, neutron, nova, sahara, m_session,
                           m_auth):
        fake_session = mock.Mock()
        fake_auth = mock.Mock()
        m_session.return_value = fake_session
        m_auth.return_value = fake_auth

        self.base_scenario._init_clients()

        sahara.assert_called_with('1.1',
                                  session=fake_session,
                                  service_type='data-processing-local',
                                  sahara_url='http://sahara_host:8386/v1.1')
        swift.assert_called_with(auth_version='2.0',
                                 user='admin',
                                 key='nova',
                                 tenant_name='admin',
                                 authurl='http://localhost:5000/v2.0')

        nova.assert_called_with('2', session=fake_session)
        neutron.assert_called_with('2.0', session=fake_session)

        m_auth.assert_called_with(auth_url='http://localhost:5000/v3',
                                  username='admin',
                                  password='nova',
                                  project_name='admin',
                                  user_domain_name='default',
                                  project_domain_name='default')
        m_session.assert_called_with(auth=fake_auth)

    @mock.patch('sahara.tests.scenario.clients.NeutronClient.get_network_id',
                return_value='mock_net')
    @mock.patch('saharaclient.client.Client',
                return_value=FakeSaharaClient())
    @mock.patch('saharaclient.api.node_group_templates.'
                'NodeGroupTemplateManager.create',
                return_value=FakeResponse(set_id='id_ng'))
    def test__create_node_group_template(self, mock_ng, mock_saharaclient,
                                         mock_neutron):
        self.base_scenario._init_clients()
        self.assertEqual({'worker': 'id_ng', 'master': 'id_ng'},
                         self.base_scenario._create_node_group_templates())

    @mock.patch('sahara.tests.scenario.clients.NeutronClient.get_network_id',
                return_value='mock_net')
    @mock.patch('saharaclient.client.Client', return_value=FakeSaharaClient())
    @mock.patch('saharaclient.api.cluster_templates.'
                'ClusterTemplateManager.create',
                return_value=FakeResponse(set_id='id_ct'))
    def test__create_cluster_template(self, mock_ct, mock_saharaclient,
                                      mock_neutron):
        self.base_scenario._init_clients()
        self.assertEqual('id_ct',
                         self.base_scenario._create_cluster_template())

    @mock.patch('sahara.tests.scenario.clients.NovaClient.get_image_id',
                return_value='mock_image')
    @mock.patch('saharaclient.client.Client', return_value=FakeSaharaClient())
    @mock.patch('saharaclient.api.clusters.ClusterManager.create',
                return_value=FakeResponse(set_id='id_cluster'))
    def test__create_cluster(self, mock_cluster_manager, mock_saharaclient,
                             mock_nova):
        self.base_scenario._init_clients()
        self.assertEqual('id_cluster',
                         self.base_scenario._create_cluster('id_ct'))

    @mock.patch('saharaclient.client.Client', return_value=FakeSaharaClient())
    @mock.patch('sahara.tests.scenario.clients.NeutronClient.get_network_id',
                return_value='mock_net')
    @mock.patch('saharaclient.api.base.ResourceManager._get',
                return_value=FakeResponse(set_status='Active'))
    @mock.patch('sahara.tests.scenario.base.BaseTestCase._check_event_logs')
    def test__poll_cluster_status(self, mock_status, mock_neutron,
                                  mock_saharaclient, mock_check_event_logs):
        self.base_scenario._init_clients()
        self.assertIsNone(
            self.base_scenario._poll_cluster_status('id_cluster'))

    @mock.patch('saharaclient.client.Client', return_value=FakeSaharaClient())
    @mock.patch('saharaclient.api.base.ResourceManager._get')
    def test_check_event_log_feature(self, mock_resp, mock_saharaclient):
        self.base_scenario._init_clients()

        self.assertIsNone(self.base_scenario._check_event_logs(
            FakeCluster(True, [])))
        self.assertIsNone(self.base_scenario._check_event_logs(
            FakeCluster(False, [{'successful': True}])))

        with testtools.ExpectedException(exc.TempestException):
            self.base_scenario._check_event_logs(
                FakeCluster(False, [{'successful': False}]))

        with testtools.ExpectedException(exc.TempestException):
            self.base_scenario._check_event_logs(
                FakeCluster(False, [{'successful': None}]))

    @mock.patch('saharaclient.api.base.ResourceManager._update',
                return_value=FakeResponse(set_id='id_internal_db_data'))
    @mock.patch('saharaclient.client.Client', return_value=FakeSaharaClient())
    def test__create_internal_db_data(self, mock_saharaclient, mock_update):
        self.base_scenario._init_clients()
        self.assertEqual('internal-db://id_internal_db_data',
                         self.base_scenario._create_internal_db_data(
                             'sahara/tests/scenario_unit/vanilla2_6_0.yaml'))

    @mock.patch('swiftclient.client.Connection.put_container',
                return_value=None)
    @mock.patch('saharaclient.client.Client', return_value=FakeSaharaClient())
    def test__create_swift_data(self, mock_saharaclient, mock_swiftclient):
        self.base_scenario._init_clients()
        self.assertTrue('swift://sahara-tests-' in
                        self.base_scenario._create_swift_data())

    @mock.patch('swiftclient.client.Connection.put_container',
                return_value=None)
    @mock.patch('saharaclient.client.Client', return_value=FakeSaharaClient())
    def test__get_swift_container(self, mock_saharaclient,
                                  mock_swiftclient):
        self.base_scenario._init_clients()
        self.assertTrue('sahara-tests-' in
                        self.base_scenario._get_swift_container())

    @mock.patch('saharaclient.api.base.ResourceManager._create',
                return_value=FakeResponse(set_id='id_for_datasource'))
    @mock.patch('swiftclient.client.Connection.put_container',
                return_value=None)
    @mock.patch('swiftclient.client.Connection.put_object',
                return_value=None)
    @mock.patch('saharaclient.client.Client', return_value=FakeSaharaClient())
    def test__create_datasources(self, mock_saharaclient,
                                 mock_swiftcontainer, mock_swiftobject,
                                 mock_create):
        self.base_scenario._init_clients()
        self.assertEqual(('id_for_datasource', 'id_for_datasource'),
                         self.base_scenario._create_datasources(
                             self.job))

    @mock.patch('saharaclient.api.base.ResourceManager._create',
                return_value=FakeResponse(set_id='id_for_job_binaries'))
    @mock.patch('swiftclient.client.Connection.put_object',
                return_value=None)
    @mock.patch('swiftclient.client.Connection.put_container',
                return_value=None)
    @mock.patch('saharaclient.client.Client', return_value=FakeSaharaClient())
    def test__create_create_job_binaries(self, mock_saharaclient,
                                         mock_swiftcontainer,
                                         mock_swiftobject,
                                         mock_sahara_create):
        self.base_scenario._init_clients()
        self.assertEqual((['id_for_job_binaries'], []),
                         self.base_scenario._create_job_binaries(
                             self.job))

    @mock.patch('saharaclient.api.base.ResourceManager._create',
                return_value=FakeResponse(set_id='id_for_job_binary'))
    @mock.patch('swiftclient.client.Connection.put_object',
                return_value=None)
    @mock.patch('swiftclient.client.Connection.put_container',
                return_value=None)
    @mock.patch('saharaclient.client.Client', return_value=FakeSaharaClient())
    def test__create_create_job_binary(self, mock_saharaclient,
                                       mock_swiftcontainer, mock_swiftobject,
                                       mock_sahara_create):
        self.base_scenario._init_clients()
        self.assertEqual('id_for_job_binary',
                         self.base_scenario._create_job_binary(self.job.get(
                             'input_datasource')))

    @mock.patch('saharaclient.api.base.ResourceManager._create',
                return_value=FakeResponse(set_id='id_for_job'))
    @mock.patch('saharaclient.client.Client', return_value=FakeSaharaClient())
    def test__create_job(self, mock_client, mock_sahara_client):
        self.base_scenario._init_clients()
        self.assertEqual('id_for_job',
                         self.base_scenario._create_job(
                             'Pig',
                             ['id_for_job_binaries'],
                             []))

    @mock.patch('sahara.tests.scenario.clients.SaharaClient.get_job_status',
                return_value='SUCCEEDED')
    @mock.patch('saharaclient.api.base.ResourceManager._get',
                return_value=FakeResponse(set_id='id_for_run_job_get'))
    @mock.patch('saharaclient.api.base.ResourceManager._create',
                return_value=FakeResponse(set_id='id_for_run_job_create'))
    @mock.patch('sahara.tests.scenario.base.BaseTestCase.'
                '_poll_cluster_status',
                return_value=None)
    @mock.patch('sahara.tests.scenario.base.BaseTestCase.'
                '_create_node_group_templates',
                return_value='id_node_group_template')
    @mock.patch('sahara.tests.scenario.base.BaseTestCase.'
                '_create_cluster_template',
                return_value='id_cluster_template')
    @mock.patch('sahara.tests.scenario.base.BaseTestCase._create_cluster',
                return_value='id_cluster')
    @mock.patch('sahara.tests.scenario.base.BaseTestCase._create_job',
                return_value='id_for_job')
    @mock.patch('sahara.tests.scenario.base.BaseTestCase._create_job_binaries',
                return_value=(['id_for_job_binaries'], []))
    @mock.patch('sahara.tests.scenario.base.BaseTestCase._create_datasources',
                return_value=('id_for_datasource', 'id_for_datasource'))
    @mock.patch('saharaclient.client.Client', return_value=FakeSaharaClient())
    def test_check_run_jobs(self, mock_saharaclient, mock_datasources,
                            mock_job_binaries, mock_job,
                            mock_node_group_template, mock_cluster_template,
                            mock_cluster, mock_cluster_status, mock_create,
                            mock_get, mock_client):
        self.base_scenario._init_clients()
        self.base_scenario.create_cluster()
        self.base_scenario.testcase["edp_jobs_flow"] = [
            {
                "type": "Pig",
                "input_datasource": {
                    "type": "swift",
                    "source": "etc/edp-examples/edp-pig/top-todoers/"
                              "data/input"
                },
                "output_datasource": {
                    "type": "hdfs",
                    "destination": "/user/hadoop/edp-output"
                },
                "main_lib": {
                    "type": "swift",
                    "source": "etc/edp-examples/edp-pig/top-todoers/"
                              "example.pig"
                }
            }
        ]
        with mock.patch('time.sleep'):
            self.assertIsNone(self.base_scenario.check_run_jobs())

    @mock.patch('sahara.tests.scenario.base.BaseTestCase.'
                '_poll_cluster_status',
                return_value=None)
    @mock.patch('saharaclient.api.base.ResourceManager._get',
                return_value=FakeResponse(set_id='id_scale_get'))
    @mock.patch('saharaclient.api.base.ResourceManager._update',
                return_value=FakeResponse(set_id='id_scale_update'))
    @mock.patch('saharaclient.client.Client', return_value=FakeSaharaClient())
    def test_check_scale(self, mock_saharaclient, mock_update, mock_get,
                         mock_poll):
        self.base_scenario._init_clients()
        self.base_scenario.ng_id_map = {'vanilla-worker': 'set_id-w',
                                        'vanilla-master': 'set_id-m'}
        self.base_scenario.ng_name_map = {'vanilla-worker': 'worker-123',
                                          'vanilla-master': 'master-321'}
        self.base_scenario.cluster_id = 'cluster_id'
        self.assertIsNone(self.base_scenario.check_scale())

    @mock.patch('saharaclient.client.Client', return_value=FakeSaharaClient())
    @mock.patch('sahara.tests.scenario.clients.NeutronClient.get_network_id',
                return_value='mock_net')
    @mock.patch('saharaclient.api.base.ResourceManager._get',
                return_value=FakeResponse(set_status='Error'))
    def test_errormsg(self, mock_status, mock_neutron, mock_saharaclient):
        self.base_scenario._init_clients()
        with testtools.ExpectedException(exc.TempestException):
            self.base_scenario._poll_cluster_status('id_cluster')
