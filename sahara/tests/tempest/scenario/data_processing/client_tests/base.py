# Copyright (c) 2014 Mirantis Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import time

from oslo.utils import timeutils
from saharaclient.api import base as sab
from saharaclient import client as sahara_client
from tempest import config
from tempest import exceptions
from tempest.openstack.common import log as logging
from tempest.scenario.data_processing import config as sahara_test_config
from tempest.scenario import manager


CONF = sahara_test_config.SAHARA_TEST_CONF
TEMPEST_CONF = config.CONF

LOG = logging.getLogger(__name__)


class BaseDataProcessingTest(manager.ScenarioTest):
    @classmethod
    def resource_setup(cls):
        cls.set_network_resources()
        super(BaseDataProcessingTest, cls).resource_setup()

        endpoint_type = TEMPEST_CONF.data_processing.endpoint_type
        catalog_type = TEMPEST_CONF.data_processing.catalog_type
        auth_url = TEMPEST_CONF.identity.uri

        credentials = cls.credentials()

        cls.client = sahara_client.Client(
            CONF.data_processing.saharaclient_version,
            credentials.username,
            credentials.password,
            project_name=credentials.tenant_name,
            endpoint_type=endpoint_type,
            service_type=catalog_type,
            auth_url=auth_url,
            sahara_url=CONF.data_processing.sahara_url)

        cls.object_client = cls.manager.object_client
        cls.container_client = cls.manager.container_client

        cls.floating_ip_pool = CONF.data_processing.floating_ip_pool
        if TEMPEST_CONF.service_available.neutron:
            cls.floating_ip_pool = cls.get_floating_ip_pool_id_for_neutron()

        cls.worker_template = {
            'description': 'Test node group template',
            'plugin_name': 'fake',
            'hadoop_version': '0.1',
            'node_processes': [
                'datanode',
                'tasktracker'
            ],
            'flavor_id': CONF.data_processing.flavor_id,
            'floating_ip_pool': cls.floating_ip_pool
        }

        cls.master_template = {
            'description': 'Test node group template',
            'plugin_name': 'fake',
            'hadoop_version': '0.1',
            'node_processes': [
                'namenode',
                'jobtracker'
            ],
            'flavor_id': CONF.data_processing.flavor_id,
            'floating_ip_pool': cls.floating_ip_pool,
            'auto_security_group': True
        }

        cls.cluster_template = {
            'description': 'Test cluster template',
            'plugin_name': 'fake',
            'hadoop_version': '0.1'
        }

        cls.swift_data_source_with_creds = {
            'url': 'swift://sahara-container/input-source',
            'description': 'Test data source',
            'type': 'swift',
            'credentials': {
                'user': 'test',
                'password': '123'
            }
        }

        cls.local_hdfs_data_source = {
            'url': 'input-source',
            'description': 'Test data source',
            'type': 'hdfs',
        }

        cls.external_hdfs_data_source = {
            'url': 'hdfs://test-master-node/usr/hadoop/input-source',
            'description': 'Test data source',
            'type': 'hdfs'
        }

    @classmethod
    def get_floating_ip_pool_id_for_neutron(cls):
        for network in cls.networks_client.list_networks()[1]:
            if network['label'] == CONF.data_processing.floating_ip_pool:
                return network['id']
        raise exceptions.NotFound(
            'Floating IP pool \'%s\' not found in pool list.'
            % CONF.data_processing.floating_ip_pool)

    def get_private_network_id(cls):
        for network in cls.networks_client.list_networks()[1]:
            if network['label'] == CONF.data_processing.private_network:
                return network['id']
        raise exceptions.NotFound(
            'Private network \'%s\' not found in network list.'
            % CONF.data_processing.private_network)

    def create_node_group_template(self, name, **kwargs):

        resp_body = self.client.node_group_templates.create(
            name, **kwargs)

        self.addCleanup(self.delete_resource,
                        self.client.node_group_templates, resp_body.id)

        return resp_body

    def create_cluster_template(self, name, **kwargs):

        resp_body = self.client.cluster_templates.create(
            name, **kwargs)

        self.addCleanup(self.delete_resource,
                        self.client.cluster_templates, resp_body.id)

        return resp_body

    def create_data_source(self, name, url, description, type,
                           credentials=None):

        user = credentials['user'] if credentials else None
        pas = credentials['password'] if credentials else None

        resp_body = self.client.data_sources.create(
            name, description, type, url, credential_user=user,
            credential_pass=pas)

        self.addCleanup(self.delete_resource,
                        self.client.data_sources, resp_body.id)

        return resp_body

    def create_job_binary(self, name, url, description, extra=None):

        resp_body = self.client.job_binaries.create(
            name, url, description, extra)

        self.addCleanup(self.delete_resource,
                        self.client.job_binaries, resp_body.id)

        return resp_body

    def create_job_binary_internal(self, name, data):

        resp_body = self.client.job_binary_internals.create(name, data)

        self.addCleanup(self.delete_resource,
                        self.client.job_binary_internals, resp_body.id)

        return resp_body

    def create_job(self, name, job_type, mains, libs=None, description=None):

        libs = libs or ()
        description = description or ''

        resp_body = self.client.jobs.create(
            name, job_type, mains, libs, description)

        self.addCleanup(self.delete_resource, self.client.jobs, resp_body.id)

        return resp_body

    def create_cluster(self, name, **kwargs):

        resp_body = self.client.clusters.create(name, **kwargs)

        self.addCleanup(self.delete_resource, self.client.clusters,
                        resp_body.id)

        return resp_body

    def check_cluster_active(self, cluster_id):
        timeout = CONF.data_processing.cluster_timeout
        s_time = timeutils.utcnow()
        while timeutils.delta_seconds(s_time, timeutils.utcnow()) < timeout:
            cluster = self.client.clusters.get(cluster_id)
            if cluster.status == 'Active':
                return
            if cluster.status == 'Error':
                raise exceptions.BuildErrorException(
                    'Cluster failed to build and is in "Error" status.')
            time.sleep(CONF.data_processing.request_timeout)
        raise exceptions.TimeoutException(
            'Cluster failed to get to "Active status within %d seconds.'
            % timeout)

    def create_job_execution(self, **kwargs):

        resp_body = self.client.job_executions.create(**kwargs)

        self.addCleanup(self.delete_resource, self.client.job_executions,
                        resp_body.id)

        return resp_body

    def create_container(self, name):

        self.container_client.create_container(name)

        self.addCleanup(self.delete_swift_container, name)

    def delete_resource(self, resource_client, resource_id):
        try:
            resource_client.delete(resource_id)
        except sab.APIException:
            pass
        else:
            self.delete_timeout(resource_client, resource_id)

    def delete_timeout(
            self, resource_client, resource_id,
            timeout=CONF.data_processing.cluster_timeout):

        start = timeutils.utcnow()
        while timeutils.delta_seconds(start, timeutils.utcnow()) < timeout:
            try:
                resource_client.get(resource_id)
            except sab.APIException as sahara_api_exception:
                if 'not found' in sahara_api_exception.message:
                    return
                raise sahara_api_exception

            time.sleep(CONF.data_processing.request_timeout)

        raise exceptions.TimeoutException(
            'Failed to delete resource "%s" in %d seconds.'
            % (resource_id, timeout))

    def delete_swift_container(self, container):
        objects = ([obj['name'] for obj in
                    self.container_client.list_all_container_objects(
                        container)])
        for obj in objects:
            self.object_client.delete_object(container, obj)
        self.container_client.delete_container(container)
