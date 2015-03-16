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

import time

import fixtures
from neutronclient.neutron import client as neutron_client
from novaclient import client as nova_client
from oslo_utils import uuidutils
from saharaclient.api import base as saharaclient_base
from saharaclient import client as sahara_client
from swiftclient import client as swift_client
from swiftclient import exceptions as swift_exc
from tempest_lib import exceptions as exc


class Client(object):
    def is_resource_deleted(self, method, *args, **kwargs):
        raise NotImplementedError

    def delete_resource(self, method, *args, **kwargs):
        # TODO(sreshetniak): make timeout configurable
        with fixtures.Timeout(300, gentle=True):
            while True:
                if self.is_resource_deleted(method, *args, **kwargs):
                    break
                time.sleep(5)


class SaharaClient(Client):
    def __init__(self, *args, **kwargs):
        self.sahara_client = sahara_client.Client('1.1', *args, **kwargs)

    def create_node_group_template(self, *args, **kwargs):
        data = self.sahara_client.node_group_templates.create(*args, **kwargs)
        return data.id

    def delete_node_group_template(self, node_group_template_id):
        return self.delete_resource(
            self.sahara_client.node_group_templates.delete,
            node_group_template_id)

    def create_cluster_template(self, *args, **kwargs):
        data = self.sahara_client.cluster_templates.create(*args, **kwargs)
        return data.id

    def delete_cluster_template(self, cluster_template_id):
        return self.delete_resource(
            self.sahara_client.cluster_templates.delete,
            cluster_template_id)

    def create_cluster(self, *args, **kwargs):
        data = self.sahara_client.clusters.create(*args, **kwargs)
        return data.id

    def delete_cluster(self, cluster_id):
        return self.delete_resource(
            self.sahara_client.clusters.delete,
            cluster_id)

    def scale_cluster(self, cluster_id, body):
        return self.sahara_client.clusters.scale(cluster_id, body)

    def create_datasource(self, *args, **kwargs):
        data = self.sahara_client.data_sources.create(*args, **kwargs)
        return data.id

    def delete_datasource(self, datasource_id):
        return self.delete_resource(
            self.sahara_client.data_sources.delete,
            datasource_id)

    def create_job_binary_internal(self, *args, **kwargs):
        data = self.sahara_client.job_binary_internals.create(*args, **kwargs)
        return data.id

    def delete_job_binary_internal(self, job_binary_internal_id):
        return self.delete_resource(
            self.sahara_client.job_binary_internals.delete,
            job_binary_internal_id)

    def create_job_binary(self, *args, **kwargs):
        data = self.sahara_client.job_binaries.create(*args, **kwargs)
        return data.id

    def delete_job_binary(self, job_binary_id):
        return self.delete_resource(
            self.sahara_client.job_binaries.delete,
            job_binary_id)

    def create_job(self, *args, **kwargs):
        data = self.sahara_client.jobs.create(*args, **kwargs)
        return data.id

    def delete_job(self, job_id):
        return self.delete_resource(
            self.sahara_client.jobs.delete,
            job_id)

    def run_job(self, *args, **kwargs):
        data = self.sahara_client.job_executions.create(*args, **kwargs)
        return data.id

    def delete_job_execution(self, job_execution_id):
        return self.delete_resource(
            self.sahara_client.job_executions.delete,
            job_execution_id)

    def get_cluster_status(self, cluster_id):
        data = self.sahara_client.clusters.get(cluster_id)
        return str(data.status)

    def get_job_status(self, exec_id):
        data = self.sahara_client.job_executions.get(exec_id)
        return str(data.info['status'])

    def is_resource_deleted(self, method, *args, **kwargs):
        try:
            method(*args, **kwargs)
        except saharaclient_base.APIException as ex:
            return ex.error_code == 404

        return False


class NovaClient(Client):
    def __init__(self, *args, **kwargs):
        self.nova_client = nova_client.Client('2', *args, **kwargs)

    def get_image_id(self, image_name):
        if uuidutils.is_uuid_like(image_name):
            return image_name
        for image in self.nova_client.images.list():
            if image.name == image_name:
                return image.id

        raise exc.NotFound(image_name)


class NeutronClient(Client):
    def __init__(self, *args, **kwargs):
        self.neutron_client = neutron_client.Client('2.0', *args, **kwargs)

    def get_network_id(self, network_name):
        if uuidutils.is_uuid_like(network_name):
            return network_name
        networks = self.neutron_client.list_networks(name=network_name)
        networks = networks['networks']
        if len(networks) < 1:
            raise exc.NotFound(network_name)
        return networks[0]['id']


class SwiftClient(Client):
    def __init__(self, *args, **kwargs):
        self.swift_client = swift_client.Connection(auth_version='2.0',
                                                    *args, **kwargs)

    def create_container(self, container_name):
        return self.swift_client.put_container(container_name)

    def delete_container(self, container_name):
        return self.delete_resource(
            self.swift_client.delete_container,
            container_name)

    def upload_data(self, container_name, object_name, data):
        return self.swift_client.put_object(container_name, object_name, data)

    def delete_object(self, container_name, object_name):
        return self.delete_resource(
            self.swift_client.delete_object,
            container_name,
            object_name)

    def is_resource_deleted(self, method, *args, **kwargs):
        try:
            method(*args, **kwargs)
        except swift_exc.ClientException as ex:
            return ex.http_status == 404

        return False
