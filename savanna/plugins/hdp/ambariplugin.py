# Copyright (c) 2013 Hortonworks, Inc.
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

import os
import requests
from savanna import context
from savanna.openstack.common import jsonutils as json
from savanna.openstack.common import log as logging
from savanna.plugins.hdp import blueprintprocessor as bp
from savanna.plugins.hdp import clusterspec
from savanna.plugins.hdp import configprovider as cfg
from savanna.plugins.hdp import hadoopserver as h
from savanna.plugins.hdp import savannautils as s
from savanna.plugins import provisioning as p

LOG = logging.getLogger(__name__)


class AmbariPlugin(p.ProvisioningPluginBase):

    def __init__(self):
        self.cluster_name_to_ambari_host_mapping = {}
        self.default_config = self._get_default_cluster_configuration()

    def create_cluster(self, cluster, cluster_template):

        if cluster_template is None:
            raise ValueError('must supply cluster template')

        cluster_spec = clusterspec.ClusterSpec(cluster_template,
                                               cluster=cluster)

        hosts = self._get_servers(cluster)

        ambari_host = self._determine_host_for_server_component(
            'AMBARI_SERVER', cluster_spec, hosts)
        self.cluster_name_to_ambari_host_mapping[cluster.name] = ambari_host

        servers = []
        for host in hosts:
            servers.append(
                h.HadoopServer(host, cluster_spec.node_groups[host.role]))

        provisioned = self._provision_cluster(cluster.name, cluster_spec,
                                              ambari_host, servers)
        if provisioned:
            #self._update_server_hosts_files(servers)
            installed = self._install_services(cluster.name, ambari_host)
            if installed:
                LOG.info("Install of Hadoop stack successful.")
                # still need ssh to configure ganglia.
                ganglia_server_ip = self._determine_host_for_server_component(
                    'GANGLIA_SERVER',
                    cluster_spec, hosts).internal_ip
                self.update_ganglia_configurations(ganglia_server_ip, servers)
            else:
                LOG.warning("Install of Hadoop stack failed.")
        else:
            LOG.warning("Provisioning of Hadoop cluster failed.")

    def _get_servers(self, cluster):
        servers = []
        if hasattr(cluster, 'node_groups') and cluster.node_groups is not None:
            # code for a savanna cluster object
            for node_group in cluster.node_groups:
                for server in node_group.instances:
                    setattr(server, 'role', node_group.name)
                    setattr(server, 'node_processes',
                            node_group.node_processes)
                    servers.append(server)
        else:
            # cluster is actually a cloud context
            servers = cluster.instances

        return servers

    def get_node_processes(self, hadoop_version):
        #TODO(jmaron): use version information
        node_processes = {}
        for service in self.default_config.services:
            components = []
            for component in service.components:
                components.append(component.name)
            node_processes[service.name] = components

        return node_processes

    def convert(self, cluster_template, config):
        with open(config, 'r') as f:
            normalized_config = clusterspec.ClusterSpec(f.read()).normalize()

        #TODO(jspeidel):  can we get the name (first arg) from somewhere?

        cluster_template = s.convert(cluster_template, normalized_config)

        return cluster_template

    def update_infra(self, cluster):
        for node_group in cluster.node_groups:
            node_group.image = cluster.default_image_id

    def convert_props_to_template(self, props):
        raise NotImplementedError('not yet supported')

    def _spawn(self, func, args):
        context.spawn(func, args)

    def _add_cluster(self, ambari_public_ip, name):
        add_cluster_url = 'http://{0}:8080/api/v1/clusters/{1}'.format(
            ambari_public_ip, name)
        #TODO(jspeidel): get stack info from advanced config
        result = requests.post(add_cluster_url,
                               data='{"Clusters": {"version" : "HDP-1.2.0"}}',
                               auth=('admin', 'admin'))
        if result.status_code != 201:
            LOG.warning(
                'Create cluster command failed. {0}'.format(result.text))
            return False

        return True

    def _add_configurations_to_cluster(self, cluster_spec, ambari_public_ip,
                                       name):
        configs = cluster_spec.configurations
        add_configuration_url = 'http://{0}:8080/api/v1/clusters/{1}'.format(
            ambari_public_ip, name)
        body = {}
        clusters = {}
        body['Clusters'] = clusters
        for config_name in configs:
            config_body = {}
            clusters['desired_config'] = config_body
            config_body['type'] = config_name
            #TODO(jspeidel): hard coding for now
            config_body['tag'] = 'v1'
            config_body['properties'] = configs[config_name]
            result = requests.put(add_configuration_url, data=json.dumps(body),
                                  auth=('admin', 'admin'))
            if result.status_code != 200:
                LOG.warning(
                    'Set configuration command failed. {0}'.format(
                        result.text))
                return False

        return True

    def _add_services_to_cluster(self, cluster_spec, ambari_public_ip, name):
        services = cluster_spec.services
        add_service_url = 'http://{0}:8080/api/v1/clusters/{1}/services/{2}'
        for service in services:
            if service.name != 'AMBARI':
                result = requests.post(
                    add_service_url.format(ambari_public_ip, name,
                                           service.name),
                    auth=('admin', 'admin'))
                if result.status_code != 201:
                    LOG.warning(
                        'Create service command failed. {0}'.format(
                            result.text))
                    return False

        return True

    def _add_components_to_services(self, cluster_spec, ambari_public_ip,
                                    name):
        add_component_url = 'http://{0}:8080/api/v1/clusters/{1}/services/{' \
                            '2}/components/{3}'
        for service in cluster_spec.services:
            if service.name != 'AMBARI':
                for component in service.components:
                    result = requests.post(add_component_url.format(
                        ambari_public_ip, name, service.name, component.name),
                        auth=('admin', 'admin'))
                    if result.status_code != 201:
                        LOG.warning(
                            'Create component command failed. {0}'.format(
                                result.text))
                        return False

        return True

    def _add_hosts_and_components(self, cluster_spec, servers,
                                  ambari_public_ip, name):
        add_host_url = 'http://{0}:8080/api/v1/clusters/{1}/hosts/{2}'
        add_host_component_url = 'http://{0}:8080/api/v1/clusters/{' \
                                 '1}/hosts/{2}/host_components/{3}'
        for host in servers:
            hostname = host.instance.fqdn.lower()
            result = requests.post(
                add_host_url.format(ambari_public_ip, name, hostname),
                auth=('admin', 'admin'))
            if result.status_code != 201:
                LOG.warning(
                    'Create host command failed. {0}'.format(result.text))
                return False
                #TODO(jspeidel): is role really same as node group?
            node_group_name = host.node_group.name
            #TODO(jspeidel): ensure that node group exists
            node_group = cluster_spec.node_groups[node_group_name]
            for component in node_group.components:
                # don't add any AMBARI components
                if component.find('AMBARI') != 0:
                    result = requests.post(add_host_component_url.format(
                        ambari_public_ip, name, hostname, component),
                        auth=('admin', 'admin'))
                    if result.status_code != 201:
                        LOG.warning(
                            'Create host_component command failed. {0}'.format(
                                result.text))
                        return False

        return True

    def _provision_cluster(self, name, cluster_spec, ambari_host, servers):
        #TODO(jspeidel): encapsulate in another class

        ambari_public_ip = ambari_host.management_ip
        ambari_private_ip = ambari_host.internal_ip

        LOG.info(
            ' Provisioning Cluster via Ambari Server: {0} ...'.format(
                ambari_public_ip))

        for server in servers:
            self._spawn(server.provision_ambari, ambari_private_ip)

        self._wait_for_host_registrations(len(servers), ambari_host)

        # add cluster
        if not self._add_cluster(ambari_public_ip, name):
            return False

        # add configurations to cluster
        if not self._add_configurations_to_cluster(cluster_spec,
                                                   ambari_public_ip, name):
            return False

        # add services
        if not self._add_services_to_cluster(cluster_spec, ambari_public_ip,
                                             name):
            return False

        # add components to services
        if not self._add_components_to_services(cluster_spec, ambari_public_ip,
                                                name):
            return False

        # add hosts and host_components
        if not self._add_hosts_and_components(cluster_spec, servers,
                                              ambari_public_ip, name):
            return False

        return True

    def _wait_for_host_registrations(self, num_hosts, ambari_host):
        LOG.info(
            'Waiting for all Ambari agents to register with server ...')

        url = 'http://{0}:8080/api/v1/hosts'.format(ambari_host.management_ip)
        result = None
        json_result = None

        #TODO(jspeidel): timeout
        while result is None or len(json_result['items']) < num_hosts:
            context.sleep(5)
            try:
                result = requests.get(url, auth=('admin', 'admin'))
                json_result = json.loads(result.text)

                # TODO(jspeidel): just for debug
                LOG.info('Registered Hosts: {0} of {1}'.format(
                    len(json_result['items']), num_hosts))
                for hosts in json_result['items']:
                    LOG.debug('Registered Host: {0}'.format(
                        hosts['Hosts']['host_name']))
            except requests.ConnectionError:
                #TODO(jspeidel): max wait time
                LOG.info('Waiting to connect to ambari server ...')

    def _determine_host_for_server_component(self, component, cluster_spec,
                                             servers):
        found_node_group = None
        node_groups = cluster_spec.node_groups
        for node_group in node_groups.values():
            if component in node_group.components:
                found_node_group = node_group.name

        for host in servers:
            if host.role == found_node_group:
                return host

        raise Exception(
            'Server component [{0}] not specified in configuration'.format(
                component))

    def _update_server_hosts_files(self, servers):
        LOG.info('Updating server hosts files ...')

        for server in servers:
            # should pass in the savanna context so that it make files mods
            # on servers
            self._spawn(server.update_hosts_file, servers)

    def _install_services(self, cluster_name, ambari_host):
        LOG.info('Installing required Hadoop services ...')

        install_url = 'http://{0}:8080/api/v1/clusters/{' \
                      '1}/services?ServiceInfo/state=INIT'.format(
                          ambari_host.management_ip, cluster_name)
        body = '{"ServiceInfo": {"state" : "INSTALLED"}}'

        result = requests.put(install_url, data=body, auth=('admin', 'admin'))

        if result.status_code == 202:
            #TODO(jspeidel) don't hard code request id
            success = self._wait_for_async_request(1, cluster_name,
                                                   ambari_host)
            if success:
                LOG.info("Install of Hadoop stack successful.")
            else:
                LOG.critical('Install command failed.')
                raise RuntimeError('Hadoop service install failed')
        else:
            LOG.critical(
                'Install command failed. {0}'.format(result.text))
            raise RuntimeError('Hadoop service install failed')

        return success

    def _wait_for_async_request(self, request_id, cluster_name, ambari_host):
        request_url = 'http://{0}:8080/api/v1/clusters/{1}/requests/{' \
                      '2}/tasks?fields=Tasks/status'.format(
                          ambari_host.management_ip, cluster_name, request_id)
        started = False
        while not started:
            result = requests.get(request_url, auth=('admin', 'admin'))
            LOG.debug(
                'async request ' + request_url + ' response:\n' + result.text)
            json_result = json.loads(result.text)
            started = True
            for items in json_result['items']:
                status = items['Tasks']['status']
                if status == 'FAILED' or status == 'ABORTED':
                    return False
                else:
                    if status != 'COMPLETED':
                        started = False

            context.sleep(5)
        return started

    def update_ganglia_configurations(self, ganglia_server_ip, servers):
        for server in servers:
            self._spawn(server._configure_ganglia, ganglia_server_ip)

    def _start_services(self, cluster_name, ambari_host):
        LOG.info('Starting Hadoop services ...')
        LOG.info('Cluster name {0}, Ambari server ip {1}'
                 .format(cluster_name, ambari_host.management_ip))
        start_url = 'http://{0}:8080/api/v1/clusters/{' \
                    '1}/services?ServiceInfo/state=INSTALLED'\
            .format(ambari_host.management_ip, cluster_name)
        body = '{"ServiceInfo": {"state" : "STARTED"}}'

        result = requests.put(start_url, data=body, auth=('admin', 'admin'))
        if result.status_code == 202:
            # don't hard code request id
            success = self._wait_for_async_request(2, cluster_name,
                                                   ambari_host)
            if success:
                LOG.info(
                    "Successfully started Hadoop cluster '{0}'.".format(
                        cluster_name))
            else:
                LOG.critical('Failed to start Hadoop cluster.')
                raise RuntimeError('Failed to start Hadoop cluster.')

        else:
            LOG.critical(
                'Start command failed. Status: {0}, response: {1}'.
                format(result.status_code, result.text))
            raise RuntimeError('Hadoop cluster start failed.')

    def _get_default_cluster_configuration(self):
        with open(os.path.join(os.path.dirname(__file__), 'resources',
                               'default-cluster.template'), 'r') as f:
            return clusterspec.ClusterSpec(f.read())

    # SAVANNA PLUGIN SPI METHODS:
    def configure_cluster(self, cluster):
        # take the user inputs from the cluster and node groups and convert
        # to a ambari blueprint
        processor = bp.BlueprintProcessor(json.load(
            open(os.path.join(os.path.dirname(__file__), 'resources',
                              'default-cluster.template'), "r")))
        processor.process_user_inputs(cluster.cluster_configs)
        processor.process_node_groups(cluster.node_groups)
        # NOTE: for the time being we are going to ignore the node group
        # level configurations.  we are not currently
        # defining node level configuration items (i.e. scope='cluster' in
        # all cases for returned configs)

        #create a cloud context

        #TODO(jmaron):  is base host name really necessary any longer?
        #cloud_ctx = ClusterContext(None, LOG)
        #self._add_instances_to_cluster_context (cloud_ctx, cluster)

        self.create_cluster(cluster, json.dumps(processor.blueprint))

    def get_versions(self):
        return ['1.3.0']

    def get_configs(self, hadoop_version):
        config_resource = cfg.ConfigurationProvider(
            json.load(open(os.path.join(os.path.dirname(__file__), 'resources',
                                        'ambari-config-resource.json'), "r")))
        return config_resource.get_config_items()

    # cluster name argument supports the non-savanna based cluster
    # creation mode
    def start_cluster(self, cluster, cluster_name=None):
        if cluster_name is None:
            cluster_name = cluster.name

        self._start_services(cluster_name,
                             self.cluster_name_to_ambari_host_mapping[
                                 cluster_name])

    def get_title(self):
        return 'Hortonworks Data Platform'

    def setup(self, conf):
        super(AmbariPlugin, self).setup(conf)

    def get_description(self):
        return 'The Hortonworks OpenStack plugin works with project ' \
               'Savanna to automate the deployment of the Hortonworks data' \
               ' platform on OpenStack based public & private clouds'
