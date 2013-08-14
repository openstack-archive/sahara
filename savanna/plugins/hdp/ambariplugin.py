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
from savanna import exceptions as exc
from savanna.openstack.common import jsonutils as json
from savanna.openstack.common import log as logging
from savanna.plugins.hdp import blueprintprocessor as bp
from savanna.plugins.hdp import clusterspec
from savanna.plugins.hdp import configprovider as cfg
from savanna.plugins.hdp import exceptions as ex
from savanna.plugins.hdp import hadoopserver as h
from savanna.plugins.hdp import savannautils as s
from savanna.plugins.hdp import validator as v
from savanna.plugins import provisioning as p

LOG = logging.getLogger(__name__)


class AmbariPlugin(p.ProvisioningPluginBase):
    def __init__(self):
        self.cluster_ambari_mapping = {}
        self.default_config = self._get_default_cluster_configuration()

    def create_cluster(self, cluster, cluster_template):

        if cluster_template is None:
            raise ValueError('must supply cluster template')

        cluster_spec = clusterspec.ClusterSpec(
            cluster_template, cluster=cluster)

        hosts = self._get_servers(cluster)
        ambari_info = self.get_ambari_info(cluster_spec)
        self.cluster_ambari_mapping[cluster.name] = ambari_info
        ambari_uri = self._get_ambari_uri(cluster_spec)

        servers = []
        for host in hosts:
            servers.append(
                h.HadoopServer(host, cluster_spec.node_groups[host.role],
                               ambari_uri=ambari_uri))

        provisioned = self._provision_cluster(
            cluster.name, cluster_spec, ambari_info, servers)

        if provisioned:
            installed = self._install_services(cluster.name, ambari_info)
            if installed:
                LOG.info("Install of Hadoop stack successful.")
                # add service urls
                self._set_cluster_info(cluster, cluster_spec, ambari_info)
            else:
                raise ex.HadoopProvisionError(
                    'Installation of Hadoop stack failed.')

        else:
            raise ex.HadoopProvisionError(
                'Provisioning of Hadoop cluster failed.')

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
        normalized_config = clusterspec.ClusterSpec(config).normalize()

        #TODO(jspeidel):  can we get the name (first arg) from somewhere?

        cluster_template = s.convert(cluster_template, normalized_config,
                                     self.get_configs(
                                         cluster_template.hadoop_version))

        return cluster_template

    def update_infra(self, cluster):
        for node_group in cluster.node_groups:
            node_group.image = cluster.default_image_id

    def convert_props_to_template(self, props):
        raise NotImplementedError('not yet supported')

    def _add_cluster(self, ambari_info, name):
        add_cluster_url = 'http://{0}/api/v1/clusters/{1}'.format(
            ambari_info.get_address(), name)
        #TODO(jspeidel): get stack info from config spec
        result = requests.post(add_cluster_url,
                               data='{"Clusters": {"version" : "HDP-1.3.0"}}',
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
                        component.name),
                        auth=(ambari_info.user, ambari_info.password))
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

    def _provision_cluster(self, name, cluster_spec, ambari_info, servers):
        #TODO(jspeidel): encapsulate in another class

        LOG.info('Provisioning Cluster via Ambari Server: {0} ...'.format(
            ambari_info.get_address()))

        for server in servers:
            context.spawn("hdp-provision-instance-%s" %
                          server.instance.hostname,
                          server.provision_ambari, ambari_info)

        self._wait_for_host_registrations(len(servers), ambari_info)
        self._set_ambari_credentials(cluster_spec, ambari_info)

        # add cluster
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

        return True

    def _wait_for_host_registrations(self, num_hosts, ambari_info):
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

    def _start_services(self, cluster_name, ambari_info):
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

    def _install_components(self, ambari_info, auth, cluster_name, servers):
        LOG.info('Starting Hadoop components while scaling up')
        LOG.info('Cluster name {0}, Ambari server ip {1}'
                 .format(cluster_name, ambari_info.get_address()))
        # query for the host components on the given hosts that are in the
        # INIT state
        body = '{"HostRoles": {"state" : "INSTALLED"}}'
        install_uri = 'http://{0}/api/v1/clusters/{' \
                      '1}/host_components?HostRoles/state=INIT&' \
                      'HostRoles/host_name.in({2})'.format(
                      ambari_info.get_address(),
                      cluster_name,
                      self._get_host_list(servers))
        self._exec_ambari_command(auth, body, install_uri)

    def _start_components(self, ambari_info, auth, cluster_name, servers):
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

    def _install_and_start_components(self, cluster_name, servers,
                                      ambari_info):
        auth = (ambari_info.user, ambari_info.password)

        self._install_components(ambari_info, auth, cluster_name, servers)

        self._start_components(ambari_info, auth, cluster_name, servers)

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

    def _get_default_cluster_configuration(self):
        with open(os.path.join(os.path.dirname(__file__), 'resources',
                               'default-cluster.template'), 'r') as f:
            return clusterspec.ClusterSpec(f.read())

    def _set_cluster_info(self, cluster, cluster_spec, ambari_info):
        info = cluster.info

        try:
            jobtracker_ip = cluster_spec.determine_host_for_server_component(
                'JOBTRACKER').management_ip
        except Exception:
            pass
        else:
            info['MapReduce'] = {
                'Web UI': 'http://%s:50030' % jobtracker_ip
            }

        try:
            namenode_ip = cluster_spec.determine_host_for_server_component(
                'NAMENODE').management_ip
        except Exception:
            pass
        else:
            info['HDFS'] = {
                'Web UI': 'http://%s:50070' % namenode_ip
            }

        info['Ambari Console'] = {
            'Web UI': 'http://%s' % ambari_info.get_address()
        }

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

    def _set_ambari_credentials(self, cluster_spec, ambari_info):
        services = cluster_spec.services
        for service in services:
            if service.name == 'AMBARI':
                is_admin_provided = False
                admin_user = ambari_info.user
                admin_password = ambari_info.password
                for u in service.users:
                    if u.name == 'admin':
                        self._update_ambari_admin_user(
                            u.password, ambari_info)
                        is_admin_provided = True
                        ambari_info.user = 'admin'
                        ambari_info.password = u.password
                    else:
                        self._add_ambari_user(u, ambari_info)
                        if 'admin' in u.groups:
                            admin_user = u.name
                            admin_password = u.password

                if not is_admin_provided:
                    if admin_user is None:
                        raise ex.HadoopProvisionError("An Ambari user in the "
                                                      "admin group must be "
                                                      "configured.")
                    ambari_info.user = admin_user
                    ambari_info.password = admin_password
                    self._delete_ambari_user('admin', ambari_info)
                break

    def _update_ambari_info_credentials(self, cluster_spec, ambari_info):
        services = cluster_spec.services
        ambari_service = next((service for service in services if
                               service.name == 'AMBARI'), None)
        if ambari_service is not None:
            admin_user = next((user for user in ambari_service.users
                               if 'admin' in user.groups), None)
            if admin_user is not None:
                ambari_info.user = admin_user.name
                ambari_info.password = admin_user.password

        LOG.info('Using "{0}" as admin user for scaling of cluster'
                 .format(ambari_info.user))

    def _update_ambari_admin_user(self, password, ambari_info):
        old_pwd = ambari_info.password
        user_url = 'http://{0}/api/v1/users/admin'.format(
            ambari_info.get_address())
        update_body = '{{"Users":{{"roles":"admin,user","password":"{0}",'\
                      '"old_password":"{1}"}} }}'.format(password, old_pwd)

        request = self._get_rest_request()
        result = request.put(user_url, data=update_body, auth=(
            ambari_info.user, ambari_info.password))

        if result.status_code != 200:
            raise ex.HadoopProvisionError('Unable to update Ambari admin user'
                                          ' credentials: {0}'.
                                          format(result.text))

    def _add_ambari_user(self, user, ambari_info):
        user_url = 'http://{0}/api/v1/users/{1}'.format(
            ambari_info.get_address(), user.name)

        create_body = '{{"Users":{{"password":"{0}","roles":"{1}"}} }}'.\
            format(user.password, '%s' % ','.join(map(str, user.groups)))

        request = self._get_rest_request()
        result = request.post(user_url, data=create_body, auth=(
            ambari_info.user, ambari_info.password))

        if result.status_code != 201:
            raise ex.HadoopProvisionError('Unable to create Ambari user: {0}'.
                                          format(result.text))

    def _delete_ambari_user(self, user_name, ambari_info):
        user_url = 'http://{0}/api/v1/users/{1}'.format(
            ambari_info.get_address(), user_name)

        request = self._get_rest_request()
        result = request.delete(user_url, auth=(
            ambari_info.user, ambari_info.password))

        if result.status_code != 200:
            raise ex.HadoopProvisionError('Unable to delete Ambari user: {0}'
                                          ' : {1}'.format(user_name,
                                          result.text))

    def _get_rest_request(self):
        return requests

    # SAVANNA PLUGIN SPI METHODS:
    def _get_blueprint_processor(self, cluster):
        processor = bp.BlueprintProcessor(json.load(
            open(os.path.join(os.path.dirname(__file__), 'resources',
                              'default-cluster.template'), "r")))
        processor.process_user_inputs(self._map_to_user_inputs(
            '1.3.0', cluster.cluster_configs))
        processor.process_node_groups(cluster.node_groups)
        return processor

    def configure_cluster(self, cluster):
        # take the user inputs from the cluster and node groups and convert
        # to a ambari blueprint
        processor = self._get_blueprint_processor(cluster)
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

    # cluster name argument supports the non-savanna cluster creation mode
    def start_cluster(self, cluster, cluster_name=None):
        if cluster_name is None:
            cluster_name = cluster.name

        self._start_services(
            cluster_name, self.cluster_ambari_mapping[cluster_name])

    def get_title(self):
        return 'Hortonworks Data Platform'

    def setup(self, conf):
        super(AmbariPlugin, self).setup(conf)

    def get_description(self):
        return 'The Hortonworks OpenStack plugin works with project ' \
               'Savanna to automate the deployment of the Hortonworks data' \
               ' platform on OpenStack based public & private clouds'

    def validate(self, cluster):
        validator = v.Validator()
        validator.validate(cluster)

    def scale_cluster(self, cluster, instances):
        processor = self._get_blueprint_processor(cluster)
        cluster_spec = clusterspec.ClusterSpec(
            json.dumps(processor.blueprint), cluster=cluster)
        ambari_uri = self._get_ambari_uri(cluster_spec)

        servers = []
        for instance in instances:
            host_role = s.get_host_role(instance)
            servers.append(h.HadoopServer(instance,
                                          cluster_spec.node_groups
                                          [host_role],
                                          ambari_uri=ambari_uri))

        ambari_info = self.get_ambari_info(cluster_spec)
        self._update_ambari_info_credentials(cluster_spec, ambari_info)

        for server in servers:
            context.spawn("hdp-scaling-instance-%s" %
                          server.instance.hostname,
                          server.provision_ambari, ambari_info)

        self._wait_for_host_registrations(self._get_num_hosts(cluster),
                                          ambari_info)

        #  now add the hosts and the component
        self._add_hosts_and_components(cluster_spec, servers,
                                       ambari_info, cluster.name)

        self._install_and_start_components(cluster.name, servers, ambari_info)

    def decommission_nodes(self, cluster, instances):
        raise exc.InvalidException('The HDP plugin does not yet support the '
                                   'decommissioning of nodes')

    def validate_scaling(self, cluster, existing, additional):
        # see if additional servers are slated for "MASTER" group
        validator = v.Validator()
        validator.validate_scaling(cluster, existing, additional)

    def _get_num_hosts(self, cluster):
        count = 0
        for node_group in cluster.node_groups:
            count += node_group.count

        return count

    def _get_host_list(self, servers):
        host_list = [server.instance.fqdn.lower() for server in servers]
        return ",".join(host_list)

    def _get_ambari_uri(self, cluster_spec):
        ambari_config = cluster_spec.configurations['ambari']
        return ambari_config.get('repo.uri', None)

    def get_ambari_info(self, cluster_spec):
        ambari_host = cluster_spec.determine_host_for_server_component(
            'AMBARI_SERVER')

        port = cluster_spec.configurations['ambari'].get(
            'server.port', '8080')

        return AmbariInfo(ambari_host, port, 'admin', 'admin')


class AmbariInfo():
    def __init__(self, host, port, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def get_address(self):
        return '{0}:{1}'.format(self.host.management_ip, self.port)
