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

import json
import logging

import pkg_resources as pkg
import requests

from savanna import context
from savanna.plugins.hdp import blueprintprocessor as bp
from savanna.plugins.hdp import clusterspec as cs
from savanna.plugins.hdp import configprovider as cfg
from savanna.plugins.hdp import exceptions as ex
from savanna.plugins.hdp.versions import abstractversionhandler as avm
from savanna import version


LOG = logging.getLogger(__name__)


class VersionHandler(avm.AbstractVersionHandler):
    config_provider = None
    version = None

    def _set_version(self, version):
        self.version = version

    def _get_config_provider(self):
        if self.config_provider is None:
            self.config_provider = cfg.ConfigurationProvider(
                json.load(pkg.resource_stream(version.version_info.package,
                          'plugins/hdp/versions/1_3_2/resources/'
                          'ambari-config-resource.json')))

        return self.config_provider

    def _get_blueprint_processor(self):
        processor = bp.BlueprintProcessor(json.loads(
            self._get_default_cluster_template()))
        return processor

    def _get_default_cluster_template(self):
        return pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/1_3_2/resources/default-cluster.template')

    def get_version(self):
        return self.version

    def get_ambari_client(self):
        return AmbariClient(self)

    def get_config_items(self):
        return self._get_config_provider().get_config_items()

    def process_cluster(self, user_inputs, node_groups):
        processor = self._get_blueprint_processor()
        processor.process_user_inputs(user_inputs)
        processor.process_node_groups(node_groups)

        return processor

    def get_applicable_target(self, name):
        return self._get_config_provider().get_applicable_target(name)

    def get_cluster_spec(self, cluster_template, cluster):
        return cs.ClusterSpec(cluster_template, cluster=cluster)

    def get_default_cluster_configuration(self):
        return cs.ClusterSpec(self._get_default_cluster_template())

    def get_node_processes(self):
        node_processes = {}
        for service in self.get_default_cluster_configuration().services:
            components = []
            for component in service.components:
                components.append(component.name)
            node_processes[service.name] = components

        return node_processes

    def install_swift_integration(self, servers):
        for server in servers:
            server.install_swift_integration()


class AmbariClient():
    def __init__(self, handler):
        self.handler = handler

    def _add_cluster(self, ambari_info, name):
        add_cluster_url = 'http://{0}/api/v1/clusters/{1}'.format(
            ambari_info.get_address(), name)
        result = requests.post(add_cluster_url,
                               data='{"Clusters": {"version" : "HDP-1.3.2"}}',
                               auth=(ambari_info.user, ambari_info.password))

        if result.status_code != 201:
            LOG.warning(
                'Create cluster command failed. {0}'.format(result.text))
            return False

        return True

    def _add_configurations_to_cluster(
            self, cluster_spec, ambari_info, name):

        configs = cluster_spec.configurations
        config_url = 'http://{0}/api/v1/clusters/{1}'.format(
            ambari_info.get_address(), name)

        body = {}
        clusters = {}
        body['Clusters'] = clusters
        for config_name in configs:
            if config_name == 'ambari':
                continue

            config_body = {}
            clusters['desired_config'] = config_body
            config_body['type'] = config_name
            #TODO(jspeidel): hard coding for now
            config_body['tag'] = 'v1'
            config_body['properties'] = configs[config_name]
            result = requests.put(config_url, data=json.dumps(body), auth=(
                ambari_info.user, ambari_info.password))
            if result.status_code != 200:
                LOG.warning(
                    'Set configuration command failed. {0}'.format(
                        result.text))
                return False

        return True

    def _add_services_to_cluster(self, cluster_spec, ambari_info, name):
        services = cluster_spec.services
        add_service_url = 'http://{0}/api/v1/clusters/{1}/services/{2}'
        for service in services:
            if service.name != 'AMBARI':
                result = requests.post(add_service_url.format(
                    ambari_info.get_address(), name, service.name),
                    auth=(ambari_info.user, ambari_info.password))
                if result.status_code != 201:
                    LOG.warning(
                        'Create service command failed. {0}'.format(
                            result.text))
                    return False

        return True

    def _add_components_to_services(self, cluster_spec, ambari_info, name):
        add_component_url = 'http://{0}/api/v1/clusters/{1}/services/{' \
                            '2}/components/{3}'
        for service in cluster_spec.services:
            if service.name != 'AMBARI':
                for component in service.components:
                    result = requests.post(add_component_url.format(
                        ambari_info.get_address(), name, service.name,
                        component.name), auth=(ambari_info.user,
                                               ambari_info.password))
                    if result.status_code != 201:
                        LOG.warning(
                            'Create component command failed. {0}'.format(
                                result.text))
                        return False

        return True

    def _add_hosts_and_components(
            self, cluster_spec, servers, ambari_info, name):

        add_host_url = 'http://{0}/api/v1/clusters/{1}/hosts/{2}'
        add_host_component_url = 'http://{0}/api/v1/clusters/{1}' \
                                 '/hosts/{2}/host_components/{3}'
        for host in servers:
            hostname = host.instance.fqdn.lower()
            result = requests.post(
                add_host_url.format(ambari_info.get_address(), name, hostname),
                auth=(ambari_info.user, ambari_info.password))
            if result.status_code != 201:
                LOG.warning(
                    'Create host command failed. {0}'.format(result.text))
                return False

            node_group_name = host.node_group.name
            #TODO(jspeidel): ensure that node group exists
            node_group = cluster_spec.node_groups[node_group_name]
            for component in node_group.components:
                # don't add any AMBARI components
                if component.find('AMBARI') != 0:
                    result = requests.post(add_host_component_url.format(
                        ambari_info.get_address(), name, hostname, component),
                        auth=(ambari_info.user, ambari_info.password))
                    if result.status_code != 201:
                        LOG.warning(
                            'Create host_component command failed. {0}'.format(
                                result.text))
                        return False

        return True

    def _install_services(self, cluster_name, ambari_info):
        LOG.info('Installing required Hadoop services ...')

        ambari_address = ambari_info.get_address()
        install_url = 'http://{0}/api/v1/clusters/{' \
                      '1}/services?ServiceInfo/state=INIT'.format(
                      ambari_address, cluster_name)
        body = '{"ServiceInfo": {"state" : "INSTALLED"}}'

        result = requests.put(install_url, data=body, auth=(
            ambari_info.user, ambari_info.password))

        if result.status_code == 202:
            #TODO(jspeidel) don't hard code request id
            success = self._wait_for_async_request(
                self._get_async_request_uri(ambari_info, cluster_name, 1),
                auth=(ambari_info.user, ambari_info.password))
            if success:
                LOG.info("Install of Hadoop stack successful.")
                self._finalize_ambari_state(ambari_info)
            else:
                LOG.critical('Install command failed.')
                raise RuntimeError('Hadoop service install failed')
        else:
            LOG.error(
                'Install command failed. {0}'.format(result.text))
            raise RuntimeError('Hadoop service install failed')

        return success

    def _get_async_request_uri(self, ambari_info, cluster_name, request_id):
        return 'http://{0}/api/v1/clusters/{1}/requests/{' \
               '2}/tasks?fields=Tasks/status'.format(
               ambari_info.get_address(), cluster_name,
               request_id)

    def _wait_for_async_request(self, request_url, auth):
        started = False
        while not started:
            result = requests.get(request_url, auth=auth)
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

    def _finalize_ambari_state(self, ambari_info):
        LOG.info('Finalizing Ambari cluster state.')

        persist_state_uri = 'http://{0}/api/v1/persist'.format(
            ambari_info.get_address())
        # this post data has non-standard format because persist
        # resource doesn't comply with Ambari API standards
        persist_data = '{ "CLUSTER_CURRENT_STATUS":' \
                       '"{\\"clusterState\\":\\"CLUSTER_STARTED_5\\"}" }'
        result = requests.post(persist_state_uri, data=persist_data,
                               auth=(ambari_info.user, ambari_info.password))

        if result.status_code != 201 and result.status_code != 202:
            LOG.warning('Finalizing of Ambari cluster state failed. {0}'.
                        format(result.text))
            raise ex.HadoopProvisionError('Unable to finalize Ambari state.')

    def start_services(self, cluster_name, ambari_info):
        LOG.info('Starting Hadoop services ...')
        LOG.info('Cluster name: {0}, Ambari server address: {1}'
                 .format(cluster_name, ambari_info.get_address()))
        start_url = 'http://{0}/api/v1/clusters/{1}/services?ServiceInfo/' \
                    'state=INSTALLED'.format(
                    ambari_info.get_address(), cluster_name)
        body = '{"ServiceInfo": {"state" : "STARTED"}}'

        auth = (ambari_info.user, ambari_info.password)
        result = requests.put(start_url, data=body, auth=auth)
        if result.status_code == 202:
            # don't hard code request id
            success = self._wait_for_async_request(
                self._get_async_request_uri(ambari_info, cluster_name, 2),
                auth=auth)
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

    def _get_rest_request(self):
        return requests

    def _exec_ambari_command(self, auth, body, cmd_uri):

        LOG.debug('PUT URI: {0}'.format(cmd_uri))
        result = requests.put(cmd_uri, data=body,
                              auth=auth)
        if result.status_code == 202:
        # don't hard code request id
            LOG.debug(
                'PUT response: {0}'.format(result.text))
            json_result = json.loads(result.text)
            href = json_result['href'] + '/tasks?fields=Tasks/status'
            success = self._wait_for_async_request(href, auth)
            if success:
                LOG.info(
                    "Successfully changed state of Hadoop components ")
            else:
                LOG.critical('Failed to change state of Hadoop '
                             'components')
                raise RuntimeError('Failed to change state of Hadoop '
                                   'components')

        else:
            LOG.error(
                'Command failed. Status: {0}, response: {1}'.
                format(result.status_code, result.text))
            raise RuntimeError('Hadoop/Ambari command failed.')

    def _get_host_list(self, servers):
        host_list = [server.instance.fqdn.lower() for server in servers]
        return ",".join(host_list)

    def _install_and_start_components(self, cluster_name, servers,
                                      ambari_info):
        auth = (ambari_info.user, ambari_info.password)
        self.install_components(ambari_info, auth, cluster_name, servers)

        self.handler.install_swift_integration(servers)

        self.start_components(ambari_info, auth, cluster_name, servers)

    def install_components(self, ambari_info, auth, cluster_name, servers):
        LOG.info('Starting Hadoop components while scaling up')
        LOG.info('Cluster name {0}, Ambari server ip {1}'
                 .format(cluster_name, ambari_info.get_address()))
        # query for the host components on the given hosts that are in the
        # INIT state
        body = '{"HostRoles": {"state" : "INSTALLED"}}'
        install_uri = 'http://{0}/api/v1/clusters/{' \
                      '1}/host_components?HostRoles/state=INIT&' \
                      'HostRoles/host_name.in({2})'.format(
                      ambari_info.get_address(), cluster_name,
                      self._get_host_list(servers))
        self._exec_ambari_command(auth, body, install_uri)

    def start_components(self, ambari_info, auth, cluster_name, servers):
        # query for all the host components on one of the hosts in the
        # INSTALLED state, then get a list of the client services in the list
        installed_uri = 'http://{0}/api/v1/clusters/{' \
                        '1}/host_components?HostRoles/state=INSTALLED&' \
                        'HostRoles/host_name.in({2})' \
            .format(ambari_info.get_address(), cluster_name,
                    self._get_host_list(servers))
        result = requests.get(installed_uri, auth=auth)
        if result.status_code == 200:
            LOG.debug(
                'GET response: {0}'.format(result.text))
            json_result = json.loads(result.text)
            items = json_result['items']
            # select non-CLIENT items
            inclusion_list = list(set([x['HostRoles']['component_name']
                                       for x in items if "CLIENT" not in
                                       x['HostRoles']['component_name']]))

            # query and start all non-client components on the given set of
            # hosts
            body = '{"HostRoles": {"state" : "STARTED"}}'
            start_uri = 'http://{0}/api/v1/clusters/{' \
                        '1}/host_components?HostRoles/state=INSTALLED&' \
                        'HostRoles/host_name.in({2})' \
                        '&HostRoles/component_name.in({3})'.format(
                        ambari_info.get_address(), cluster_name,
                        self._get_host_list(servers),
                        ",".join(inclusion_list))
            self._exec_ambari_command(auth, body, start_uri)
        else:
            raise RuntimeError('Unable to determine installed service '
                               'components in scaled instances.  status'
                               ' code returned = {0}'.format(result.status))

    def wait_for_host_registrations(self, num_hosts, ambari_info):
        LOG.info(
            'Waiting for all Ambari agents to register with server ...')

        url = 'http://{0}/api/v1/hosts'.format(ambari_info.get_address())
        result = None
        json_result = None

        #TODO(jspeidel): timeout
        while result is None or len(json_result['items']) < num_hosts:
            context.sleep(5)
            try:
                result = requests.get(url, auth=(ambari_info.user,
                                                 ambari_info.password))
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

    def update_ambari_admin_user(self, password, ambari_info):
        old_pwd = ambari_info.password
        user_url = 'http://{0}/api/v1/users/admin'.format(
            ambari_info.get_address())
        update_body = '{{"Users":{{"roles":"admin,user","password":"{0}",' \
                      '"old_password":"{1}"}} }}'.format(password, old_pwd)

        request = self._get_rest_request()
        result = request.put(user_url, data=update_body, auth=(
            ambari_info.user, ambari_info.password))

        if result.status_code != 200:
            raise ex.HadoopProvisionError('Unable to update Ambari admin user'
                                          ' credentials: {0}'.format(
                                          result.text))

    def add_ambari_user(self, user, ambari_info):
        user_url = 'http://{0}/api/v1/users/{1}'.format(
            ambari_info.get_address(), user.name)

        create_body = '{{"Users":{{"password":"{0}","roles":"{1}"}} }}'. \
            format(user.password, '%s' % ','.join(map(str, user.groups)))

        request = self._get_rest_request()
        result = request.post(user_url, data=create_body, auth=(
            ambari_info.user, ambari_info.password))

        if result.status_code != 201:
            raise ex.HadoopProvisionError(
                'Unable to create Ambari user: {0}'.format(result.text))

    def delete_ambari_user(self, user_name, ambari_info):
        user_url = 'http://{0}/api/v1/users/{1}'.format(
            ambari_info.get_address(), user_name)

        request = self._get_rest_request()
        result = request.delete(user_url, auth=(
            ambari_info.user, ambari_info.password))

        if result.status_code != 200:
            raise ex.HadoopProvisionError('Unable to delete Ambari user: {0}'
                                          ' : {1}'.format(user_name,
                                                          result.text))

    def scale_cluster(self, name, cluster_spec, servers, num_hosts,
                      ambari_info):
        self.wait_for_host_registrations(num_hosts, ambari_info)

        #  now add the hosts and the component
        self._add_hosts_and_components(cluster_spec, servers,
                                       ambari_info, name)

        self._install_and_start_components(name, servers, ambari_info)

    def provision_cluster(self, cluster_spec, servers, ambari_info, name):
        if not self._add_cluster(ambari_info, name):
            return False

        # add configurations to cluster
        if not self._add_configurations_to_cluster(cluster_spec,
                                                   ambari_info, name):
            return False

        # add services
        if not self._add_services_to_cluster(cluster_spec,
                                             ambari_info, name):
            return False

        # add components to services
        if not self._add_components_to_services(cluster_spec,
                                                ambari_info, name):
            return False

        # add hosts and host_components
        if not self._add_hosts_and_components(cluster_spec, servers,
                                              ambari_info, name):
            return False

        if not self._install_services(name, ambari_info):
            return False

        self.handler.install_swift_integration(servers)

        return True
