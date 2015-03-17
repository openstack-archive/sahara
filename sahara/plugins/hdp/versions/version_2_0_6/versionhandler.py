# Copyright (c) 2014 Hortonworks, Inc.
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

from oslo_config import cfg
from oslo_log import log as logging
import pkg_resources as pkg
import six

from sahara import context
from sahara import exceptions as exc
from sahara.i18n import _
from sahara.i18n import _LE
from sahara.i18n import _LI
from sahara.i18n import _LW
from sahara.plugins import exceptions as ex
from sahara.plugins.hdp import clusterspec as cs
from sahara.plugins.hdp import configprovider as cfgprov
from sahara.plugins.hdp.versions import abstractversionhandler as avm
from sahara.plugins.hdp.versions.version_2_0_6 import edp_engine
from sahara.plugins.hdp.versions.version_2_0_6 import services
from sahara.utils import general as g
from sahara import version


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def _check_ambari(obj):
    try:
        obj.is_ambari_info()
        return obj.get_cluster()
    except AttributeError:
        return None


class VersionHandler(avm.AbstractVersionHandler):
    config_provider = None
    version = None
    client = None

    def _set_version(self, version):
        self.version = version

    def _get_config_provider(self):
        if self.config_provider is None:
            self.config_provider = cfgprov.ConfigurationProvider(
                json.load(pkg.resource_stream(
                          version.version_info.package,
                          'plugins/hdp/versions/version_2_0_6/resources/'
                          'ambari-config-resource.json')))

        return self.config_provider

    def get_version(self):
        return self.version

    def get_ambari_client(self):
        if not self.client:
            self.client = AmbariClient(self)

        return self.client

    def get_config_items(self):
        return self._get_config_provider().get_config_items()

    def get_applicable_target(self, name):
        return self._get_config_provider().get_applicable_target(name)

    def get_cluster_spec(self, cluster, user_inputs,
                         scaled_groups=None, cluster_template=None):
        if cluster_template:
            cluster_spec = cs.ClusterSpec(cluster_template, '2.0.6')
        else:
            cluster_spec = self.get_default_cluster_configuration()
            cluster_spec.create_operational_config(
                cluster, user_inputs, scaled_groups)

            cs.validate_number_of_datanodes(
                cluster, scaled_groups, self.get_config_items())

        return cluster_spec

    def get_default_cluster_configuration(self):
        return cs.ClusterSpec(self._get_default_cluster_template(), '2.0.6')

    def _get_default_cluster_template(self):
        return pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/version_2_0_6/resources/'
            'default-cluster.template')

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

    def get_services_processor(self):
        return services

    def get_edp_engine(self, cluster, job_type):
        if job_type in edp_engine.EdpOozieEngine.get_supported_job_types():
            return edp_engine.EdpOozieEngine(cluster)
        return None

    def get_edp_job_types(self):
        return edp_engine.EdpOozieEngine.get_supported_job_types()

    def get_edp_config_hints(self, job_type):
        return edp_engine.EdpOozieEngine.get_possible_job_config(job_type)

    def get_open_ports(self, node_group):
        ports = [8660]  # for Ganglia

        ports_map = {
            'AMBARI_SERVER': [8080, 8440, 8441],
            'NAMENODE': [50070, 50470, 8020, 9000],
            'DATANODE': [50075, 50475, 50010, 8010],
            'SECONDARY_NAMENODE': [50090],
            'HISTORYSERVER': [19888],
            'RESOURCEMANAGER': [8025, 8041, 8050, 8088],
            'NODEMANAGER': [45454],
            'HIVE_SERVER': [10000],
            'HIVE_METASTORE': [9083],
            'HBASE_MASTER': [60000, 60010],
            'HBASE_REGIONSERVER': [60020, 60030],
            'WEBHCAT_SERVER': [50111],
            'GANGLIA_SERVER': [8661, 8662, 8663, 8651],
            'MYSQL_SERVER': [3306],
            'OOZIE_SERVER': [11000, 11001],
            'ZOOKEEPER_SERVER': [2181, 2888, 3888],
            'NAGIOS_SERVER': [80]
        }
        for process in node_group.node_processes:
            if process in ports_map:
                ports.extend(ports_map[process])

        return ports


class AmbariClient(object):

    def __init__(self, handler):
        #  add an argument for neutron discovery
        self.handler = handler

    def _get_http_session(self, host, port):
        return host.remote().get_http_client(port)

    def _get_standard_headers(self):
        return {"X-Requested-By": "sahara"}

    def _post(self, url, ambari_info, data=None):
        session = self._get_http_session(ambari_info.host, ambari_info.port)
        return session.post(url, data=data,
                            auth=(ambari_info.user, ambari_info.password),
                            headers=self._get_standard_headers())

    def _delete(self, url, ambari_info):
        session = self._get_http_session(ambari_info.host, ambari_info.port)
        return session.delete(url,
                              auth=(ambari_info.user, ambari_info.password),
                              headers=self._get_standard_headers())

    def _put(self, url, ambari_info, data=None):
        session = self._get_http_session(ambari_info.host, ambari_info.port)
        auth = (ambari_info.user, ambari_info.password)
        return session.put(url, data=data, auth=auth,
                           headers=self._get_standard_headers())

    def _get(self, url, ambari_info):
        session = self._get_http_session(ambari_info.host, ambari_info.port)
        return session.get(url, auth=(ambari_info.user, ambari_info.password),
                           headers=self._get_standard_headers())

    def _add_cluster(self, ambari_info, name):
        add_cluster_url = 'http://{0}/api/v1/clusters/{1}'.format(
            ambari_info.get_address(), name)
        result = self._post(add_cluster_url, ambari_info,
                            data='{"Clusters": {"version" : "HDP-' +
                            self.handler.get_version() + '"}}')

        if result.status_code != 201:
            LOG.error(_LE('Create cluster command failed. {result}').format(
                result=result.text))
            raise ex.HadoopProvisionError(
                _('Failed to add cluster: %s') % result.text)

    def _add_configurations_to_cluster(
            self, cluster_spec, ambari_info, name):

        existing_config_url = ('http://{0}/api/v1/clusters/{1}?fields='
                               'Clusters/desired_configs'.format(
                                   ambari_info.get_address(), name))

        result = self._get(existing_config_url, ambari_info)

        json_result = json.loads(result.text)
        existing_configs = json_result['Clusters']['desired_configs']

        configs = cluster_spec.get_deployed_configurations()
        if 'ambari' in configs:
            configs.remove('ambari')
        if len(configs) == len(existing_configs):
            # nothing to do
            return

        config_url = 'http://{0}/api/v1/clusters/{1}'.format(
            ambari_info.get_address(), name)

        body = {}
        clusters = {}
        version = 1
        body['Clusters'] = clusters
        for config_name in configs:
            if config_name in existing_configs:
                if config_name == 'core-site' or config_name == 'global':
                    existing_version = (existing_configs[config_name]['tag']
                                        .lstrip('v'))
                    version = int(existing_version) + 1
                else:
                    continue

            config_body = {}
            clusters['desired_config'] = config_body
            config_body['type'] = config_name
            config_body['tag'] = 'v%s' % version
            config_body['properties'] = (
                cluster_spec.configurations[config_name])
            result = self._put(config_url, ambari_info, data=json.dumps(body))
            if result.status_code != 200:
                LOG.error(
                    _LE('Set configuration command failed. {result}').format(
                        result=result.text))
                raise ex.HadoopProvisionError(
                    _('Failed to set configurations on cluster: %s')
                    % result.text)

    def _add_services_to_cluster(self, cluster_spec, ambari_info, name):
        services = cluster_spec.services
        add_service_url = 'http://{0}/api/v1/clusters/{1}/services/{2}'
        for service in services:
            # Make sure the service is deployed and is managed by Ambari
            if service.deployed and service.ambari_managed:
                result = self._post(add_service_url.format(
                    ambari_info.get_address(), name, service.name),
                    ambari_info)
                if result.status_code not in [201, 409]:
                    LOG.error(
                        _LE('Create service command failed. {result}').format(
                            result=result.text))
                    raise ex.HadoopProvisionError(
                        _('Failed to add services to cluster: %s')
                        % result.text)

    def _add_components_to_services(self, cluster_spec, ambari_info, name):
        add_component_url = ('http://{0}/api/v1/clusters/{1}/services/{'
                             '2}/components/{3}')
        for service in cluster_spec.services:
            # Make sure the service is deployed and is managed by Ambari
            if service.deployed and service.ambari_managed:
                for component in service.components:
                    result = self._post(add_component_url.format(
                        ambari_info.get_address(), name, service.name,
                        component.name),
                        ambari_info)
                    if result.status_code not in [201, 409]:
                        LOG.error(
                            _LE('Create component command failed. {result}')
                            .format(result=result.text))
                        raise ex.HadoopProvisionError(
                            _('Failed to add components to services: %s')
                            % result.text)

    def _add_hosts_and_components(
            self, cluster_spec, servers, ambari_info, name):

        add_host_url = 'http://{0}/api/v1/clusters/{1}/hosts/{2}'
        add_host_component_url = ('http://{0}/api/v1/clusters/{1}'
                                  '/hosts/{2}/host_components/{3}')
        for host in servers:
            hostname = host.instance.fqdn().lower()
            result = self._post(
                add_host_url.format(ambari_info.get_address(), name, hostname),
                ambari_info)
            if result.status_code != 201:
                LOG.error(
                    _LE('Create host command failed. {result}').format(
                        result=result.text))
                raise ex.HadoopProvisionError(
                    _('Failed to add host: %s') % result.text)

            node_group_name = host.node_group.name
            # TODO(jspeidel): ensure that node group exists
            node_group = cluster_spec.node_groups[node_group_name]
            for component in node_group.components:
                # Don't add any AMBARI or HUE components
                # TODO(rlevas): Pragmatically determine if component is
                #   managed by Ambari
                if (component.find('AMBARI') != 0
                        and component.find('HUE') != 0):
                    result = self._post(add_host_component_url.format(
                        ambari_info.get_address(), name, hostname, component),
                        ambari_info)
                    if result.status_code != 201:
                        LOG.error(
                            _LE('Create host_component command failed. '
                                '{result}').format(result=result.text))
                        raise ex.HadoopProvisionError(
                            _('Failed to add host component: %s')
                            % result.text)

    def _install_services(self, cluster_name, ambari_info):
        ambari_address = ambari_info.get_address()
        install_url = ('http://{0}/api/v1/clusters/{'
                       '1}/services?ServiceInfo/state=INIT'.format(
                           ambari_address, cluster_name))
        body = ('{"RequestInfo" : { "context" : "Install all services" },'
                '"Body" : {"ServiceInfo": {"state" : "INSTALLED"}}}')

        result = self._put(install_url, ambari_info, data=body)

        if result.status_code == 202:
            json_result = json.loads(result.text)
            request_id = json_result['Requests']['id']
            success = self._wait_for_async_request(self._get_async_request_uri(
                ambari_info, cluster_name, request_id),
                ambari_info)
            if success:
                LOG.info(_LI("Install of Hadoop stack successful."))
                self._finalize_ambari_state(ambari_info)
            else:
                LOG.error(_LE('Install command failed.'))
                raise ex.HadoopProvisionError(
                    _('Installation of Hadoop stack failed.'))
        elif result.status_code != 200:
            LOG.error(
                _LE('Install command failed. {result}').format(
                    result=result.text))
            raise ex.HadoopProvisionError(
                _('Installation of Hadoop stack failed.'))

    def _get_async_request_uri(self, ambari_info, cluster_name, request_id):
        return ('http://{0}/api/v1/clusters/{1}/requests/{'
                '2}/tasks?fields=Tasks/status'.format(
                    ambari_info.get_address(), cluster_name,
                    request_id))

    # Returns the top-level requests API URI
    def _get_command_request_uri(self, ambari_info, cluster_name):
        return ('http://{0}/api/v1/clusters/{1}/requests'.format(
            ambari_info.get_address(), cluster_name))

    def _wait_for_async_request(self, request_url, ambari_info):
        started = False
        while not started:
            result = self._get(request_url, ambari_info)
            LOG.debug('Async request url: {url}  response:\n{response}'.format(
                url=request_url, response=result.text))
            json_result = json.loads(result.text)
            started = True
            for items in json_result['items']:
                status = items['Tasks']['status']
                if (status == 'FAILED' or status == 'ABORTED' or
                        status == 'TIMEDOUT'):
                    return False
                else:
                    if status != 'COMPLETED':
                        started = False

            context.sleep(5)
        return started

    def _finalize_ambari_state(self, ambari_info):
        persist_state_uri = 'http://{0}/api/v1/persist'.format(
            ambari_info.get_address())
        # this post data has non-standard format because persist
        # resource doesn't comply with Ambari API standards
        persist_data = ('{ "CLUSTER_CURRENT_STATUS":'
                        '"{\\"clusterState\\":\\"CLUSTER_STARTED_5\\"}" }')
        result = self._post(persist_state_uri, ambari_info, data=persist_data)

        if result.status_code != 201 and result.status_code != 202:
            LOG.warning(_LW('Ambari cluster state not finalized. {result}').
                        format(result=result.text))
            raise ex.HadoopProvisionError(
                _('Unable to finalize Ambari state.'))
        LOG.info(_LI('Ambari cluster state finalized.'))

    def start_services(self, cluster_name, cluster_spec, ambari_info):
        start_url = ('http://{0}/api/v1/clusters/{1}/services?ServiceInfo/'
                     'state=INSTALLED'.format(
                         ambari_info.get_address(), cluster_name))
        body = ('{"RequestInfo" : { "context" : "Start all services" },'
                '"Body" : {"ServiceInfo": {"state" : "STARTED"}}}')

        self._fire_service_start_notifications(
            cluster_name, cluster_spec, ambari_info)
        result = self._put(start_url, ambari_info, data=body)
        if result.status_code == 202:
            json_result = json.loads(result.text)
            request_id = json_result['Requests']['id']
            success = self._wait_for_async_request(
                self._get_async_request_uri(ambari_info, cluster_name,
                                            request_id), ambari_info)
            if success:
                LOG.info(
                    _LI("Successfully started Hadoop cluster '{name}'.")
                    .format(name=cluster_name))
                LOG.info(_LI('Cluster name: {cluster_name}, Ambari server '
                             'address: {server_address}').format(
                         cluster_name=cluster_name,
                         server_address=ambari_info.get_address()))
            else:
                LOG.error(_LE('Failed to start Hadoop cluster.'))
                raise ex.HadoopProvisionError(
                    _('Start of Hadoop services failed.'))

        elif result.status_code != 200:
            LOG.error(
                _LE('Start command failed. Status: {status}, response: '
                    '{response}').format(status=result.status_code,
                                         response=result.text))
            raise ex.HadoopProvisionError(
                _('Start of Hadoop services failed.'))

    def _exec_ambari_command(self, ambari_info, body, cmd_uri):

        LOG.debug('PUT URI: {uri}'.format(uri=cmd_uri))
        result = self._put(cmd_uri, ambari_info, data=body)
        if result.status_code == 202:
            LOG.debug(
                'PUT response: {result}'.format(result=result.text))
            json_result = json.loads(result.text)
            href = json_result['href'] + '/tasks?fields=Tasks/status'
            success = self._wait_for_async_request(href, ambari_info)
            if success:
                LOG.info(
                    _LI("Successfully changed state of Hadoop components "))
            else:
                LOG.error(_LE('Failed to change state of Hadoop components'))
                raise ex.HadoopProvisionError(
                    _('Failed to change state of Hadoop components'))

        else:
            LOG.error(
                _LE('Command failed. Status: {status}, response: '
                    '{response}').format(status=result.status_code,
                                         response=result.text))
            raise ex.HadoopProvisionError(_('Hadoop/Ambari command failed.'))

    def _get_host_list(self, servers):
        host_list = [server.instance.fqdn().lower() for server in servers]
        return ",".join(host_list)

    def _install_and_start_components(self, cluster_name, servers,
                                      ambari_info, cluster_spec):

        auth = (ambari_info.user, ambari_info.password)
        self._install_components(ambari_info, auth, cluster_name, servers)
        self.handler.install_swift_integration(servers)
        self._start_components(ambari_info, auth, cluster_name,
                               servers, cluster_spec)

    def _install_components(self, ambari_info, auth, cluster_name, servers):
        # query for the host components on the given hosts that are in the
        # INIT state
        # TODO(jspeidel): provide request context
        body = '{"HostRoles": {"state" : "INSTALLED"}}'
        install_uri = ('http://{0}/api/v1/clusters/{'
                       '1}/host_components?HostRoles/state=INIT&'
                       'HostRoles/host_name.in({2})'.format(
                           ambari_info.get_address(), cluster_name,
                           self._get_host_list(servers)))
        self._exec_ambari_command(ambari_info, body, install_uri)
        LOG.info(_LI('Started Hadoop components while scaling up'))
        LOG.info(_LI('Cluster name {cluster_name}, Ambari server ip {ip}')
                 .format(cluster_name=cluster_name,
                         ip=ambari_info.get_address()))

    def _start_components(self, ambari_info, auth, cluster_name, servers,
                          cluster_spec):
        # query for all the host components in the INSTALLED state,
        # then get a list of the client services in the list
        installed_uri = ('http://{0}/api/v1/clusters/{'
                         '1}/host_components?HostRoles/state=INSTALLED&'
                         'HostRoles/host_name.in({2})'.format(
                             ambari_info.get_address(), cluster_name,
                             self._get_host_list(servers)))
        result = self._get(installed_uri, ambari_info)
        if result.status_code == 200:
            LOG.debug(
                'GET response: {result}'.format(result=result.text))
            json_result = json.loads(result.text)
            items = json_result['items']

            client_set = cluster_spec.get_components_for_type('CLIENT')
            inclusion_list = list(set([x['HostRoles']['component_name']
                                       for x in items
                                       if x['HostRoles']['component_name']
                                       not in client_set]))

            # query and start all non-client components on the given set of
            # hosts
            # TODO(jspeidel): Provide request context
            body = '{"HostRoles": {"state" : "STARTED"}}'
            start_uri = ('http://{0}/api/v1/clusters/{'
                         '1}/host_components?HostRoles/state=INSTALLED&'
                         'HostRoles/host_name.in({2})'
                         '&HostRoles/component_name.in({3})'.format(
                             ambari_info.get_address(), cluster_name,
                             self._get_host_list(servers),
                             ",".join(inclusion_list)))
            self._exec_ambari_command(ambari_info, body, start_uri)
        else:
            raise ex.HadoopProvisionError(
                _('Unable to determine installed service '
                  'components in scaled instances.  status'
                  ' code returned = {0}').format(result.status))

    @g.await_process(
        3600, 5, _("Ambari agents registering with server"), _check_ambari)
    def wait_for_host_registrations(self, num_hosts, ambari_info):
        url = 'http://{0}/api/v1/hosts'.format(ambari_info.get_address())
        try:
            result = self._get(url, ambari_info)
            json_result = json.loads(result.text)

            LOG.info(_LI('Registered Hosts: {current_number} '
                         'of {final_number}').format(
                     current_number=len(json_result['items']),
                     final_number=num_hosts))
            for hosts in json_result['items']:
                LOG.debug('Registered Host: {host}'.format(
                    host=hosts['Hosts']['host_name']))
            return result and len(json_result['items']) >= num_hosts
        except Exception:
            LOG.debug('Waiting to connect to ambari server')
            return False

    def update_ambari_admin_user(self, password, ambari_info):
        old_pwd = ambari_info.password
        user_url = 'http://{0}/api/v1/users/admin'.format(
            ambari_info.get_address())
        update_body = ('{{"Users":{{"roles":"admin","password":"{0}",'
                       '"old_password":"{1}"}} }}'.format(password, old_pwd))

        result = self._put(user_url, ambari_info, data=update_body)

        if result.status_code != 200:
            raise ex.HadoopProvisionError(_('Unable to update Ambari admin '
                                            'user credentials: {0}').format(
                result.text))

    def add_ambari_user(self, user, ambari_info):
        user_url = 'http://{0}/api/v1/users/{1}'.format(
            ambari_info.get_address(), user.name)

        create_body = ('{{"Users":{{"password":"{0}","roles":"{1}"}} }}'.
                       format(user.password, '%s' % ','.
                              join(map(str, user.groups))))

        result = self._post(user_url, ambari_info, data=create_body)

        if result.status_code != 201:
            raise ex.HadoopProvisionError(
                _('Unable to create Ambari user: {0}').format(result.text))

    def delete_ambari_user(self, user_name, ambari_info):
        user_url = 'http://{0}/api/v1/users/{1}'.format(
            ambari_info.get_address(), user_name)

        result = self._delete(user_url, ambari_info)

        if result.status_code != 200:
            raise ex.HadoopProvisionError(
                _('Unable to delete Ambari user: %(user_name)s'
                  ' : %(text)s') %
                {'user_name': user_name, 'text': result.text})

    def configure_scaled_cluster_instances(self, name, cluster_spec,
                                           num_hosts, ambari_info):
        self.wait_for_host_registrations(num_hosts, ambari_info)
        self._add_configurations_to_cluster(
            cluster_spec, ambari_info, name)
        self._add_services_to_cluster(
            cluster_spec, ambari_info, name)
        self._add_components_to_services(
            cluster_spec, ambari_info, name)
        self._install_services(name, ambari_info)

    def start_scaled_cluster_instances(self, name, cluster_spec, servers,
                                       ambari_info):
        self.start_services(name, cluster_spec, ambari_info)
        self._add_hosts_and_components(
            cluster_spec, servers, ambari_info, name)
        self._install_and_start_components(
            name, servers, ambari_info, cluster_spec)

    def decommission_cluster_instances(self, cluster, clusterspec, instances,
                                       ambari_info):

        request_uri = self._get_command_request_uri(ambari_info, cluster.name)

        hosts_to_decommission = []
        # Decommission HDFS datanodes to avoid loss of data
        # during decommissioning process
        for instance in instances:
            ng_name = instance.node_group.name
            if "DATANODE" in clusterspec.node_groups[ng_name].components:
                # determine the instances that include HDFS support
                hosts_to_decommission.append(instance.fqdn())

        LOG.debug('AmbariClient: hosts_to_decommission = {hosts}'.format(
            hosts=str(hosts_to_decommission)))

        # template for request body
        body_header = ('{"RequestInfo" : { "context": "Decommission DataNode",'
                       ' "command" : "DECOMMISSION", "service_name" : "HDFS",'
                       ' "component_name" : "NAMENODE", '
                       ' "parameters" : { "slave_type" : "DATANODE", ')

        excluded_hosts_request = '"excluded_hosts" : "{0}"'

        # generate comma-separated list of hosts to de-commission
        list_of_hosts = ",".join(hosts_to_decommission)

        LOG.debug('AmbariClient: list_of_hosts = {hosts}'.format(
            hosts=list_of_hosts))

        # create the request body
        request_body = (
            body_header +
            excluded_hosts_request.format(list_of_hosts)
            + '}}'
            + ', "Requests/resource_filters":[{"service_name":"HDFS",'
            '"component_name":"NAMENODE"}]}')

        LOG.debug('AmbariClient: about to make decommission request, uri = '
                  '{uri}'.format(uri=request_uri))
        LOG.debug('AmbariClient: about to make decommission request, '
                  'request body  = {body}'.format(body=request_body))

        # ask Ambari to decommission the datanodes
        result = self._post(request_uri, ambari_info, request_body)
        if result.status_code != 202:
            LOG.error(_LE('AmbariClient: error while making decommission post '
                          'request. Error is = {result}').format(
                              result=result.text))
            raise ex.DecommissionError(
                _('An error occurred while trying to '
                  'decommission the DataNode instances that are '
                  'being shut down. '
                  'Please consult the Ambari server logs on the '
                  'master node for '
                  'more information about the failure.'))
        else:
            LOG.info(_LI('AmbariClient: decommission post request succeeded!'))

        status_template = ('http://{0}/api/v1/clusters/{1}/hosts/{2}/'
                           'host_components/{3}')

        # find the host that the NameNode is deployed on
        name_node_host = clusterspec.determine_component_hosts(
            'NAMENODE').pop()
        status_request = status_template.format(
            ambari_info.get_address(),
            cluster.name, name_node_host.fqdn(),
            'NAMENODE')

        LOG.debug('AmbariClient: about to make decommission status request,'
                  'uri = {uri}'.format(uri=status_request))

        count = 0
        while count < 100 and len(hosts_to_decommission) > 0:
            LOG.debug('AmbariClient: number of hosts waiting for '
                      'decommissioning to complete = {count}'.format(
                          count=str(len(hosts_to_decommission))))

            result = self._get(status_request, ambari_info)
            if result.status_code != 200:
                LOG.error(_LE('AmbariClient: error in making decommission '
                              'status request, error = {result}').format(
                          result=result.text))
            else:
                LOG.info(_LI('AmbariClient: decommission status request ok, '
                             'result = {result}').format(result=result.text))
                json_result = json.loads(result.text)
                live_nodes = (
                    json_result['metrics']['dfs']['namenode']['LiveNodes'])
                # parse out the map of live hosts associated with the NameNode
                json_result_nodes = json.loads(live_nodes)
                for node, val in six.iteritems(json_result_nodes):
                    admin_state = val['adminState']
                    if admin_state == 'Decommissioned':
                        LOG.debug('AmbariClient: node = {node} is '
                                  'now in adminState = {admin_state}'.format(
                                      node=node, admin_state=admin_state))
                        # remove from list, to track which nodes
                        # are now in Decommissioned state
                        hosts_to_decommission.remove(node)

            LOG.debug('AmbariClient: sleeping for 5 seconds')
            context.sleep(5)

            # increment loop counter
            count += 1

        if len(hosts_to_decommission) > 0:
            LOG.error(_LE('AmbariClient: decommissioning process timed-out '
                          'waiting for nodes to enter "Decommissioned" '
                          'status.'))

    def provision_cluster(self, cluster_spec, servers, ambari_info, name):
        self._add_cluster(ambari_info, name)
        self._add_configurations_to_cluster(cluster_spec, ambari_info, name)
        self._add_services_to_cluster(cluster_spec, ambari_info, name)
        self._add_components_to_services(cluster_spec, ambari_info, name)
        self._add_hosts_and_components(
            cluster_spec, servers, ambari_info, name)

        self._install_services(name, ambari_info)
        self.handler.install_swift_integration(servers)

    def cleanup(self, ambari_info):
        try:
            ambari_info.host.remote().close_http_session(ambari_info.port)
        except exc.NotFoundException:
            LOG.debug("HTTP session is not cached")

    def _get_services_in_state(self, cluster_name, ambari_info, state):
        services_url = ('http://{0}/api/v1/clusters/{1}/services?'
                        'ServiceInfo/state.in({2})'.format(
                            ambari_info.get_address(), cluster_name, state))

        result = self._get(services_url, ambari_info)

        json_result = json.loads(result.text)
        services = []
        for service in json_result['items']:
            services.append(service['ServiceInfo']['service_name'])

        return services

    def _fire_service_start_notifications(self, cluster_name,
                                          cluster_spec, ambari_info):
        started_services = self._get_services_in_state(
            cluster_name, ambari_info, 'STARTED')

        for service in cluster_spec.services:
            if service.deployed and service.name not in started_services:
                service.pre_service_start(cluster_spec, ambari_info,
                                          started_services)

    def setup_hdfs_ha(self, cluster_spec, servers, ambari_info, name):

        # Get HA cluster map
        hac = self._hdfs_ha_cluster_map(cluster_spec, servers,
                                        ambari_info, name)

        # start active namenode in order to format and save namesapce
        self._hdfs_ha_update_host_component(hac, hac['nn_active'],
                                            'NAMENODE', 'STARTED')

        hac['server_active'].set_namenode_safemode(hac['java_home'])
        hac['server_active'].save_namenode_namespace(hac['java_home'])

        # shutdown active namenode
        self._hdfs_ha_update_host_component(hac, hac['nn_active'],
                                            'NAMENODE', 'INSTALLED')

        # Install HDFS_CLIENT on namenodes, to be used later for updating
        # HDFS configs
        if hac['nn_active'] not in hac['hdfsc_hosts']:
            self._hdfs_ha_add_host_component(hac, hac['nn_active'],
                                             'HDFS_CLIENT')
        if hac['nn_standby'] not in hac['hdfsc_hosts']:
            self._hdfs_ha_add_host_component(hac, hac['nn_standby'],
                                             'HDFS_CLIENT')

        # start the journal_nodes
        for jn in hac['jn_hosts']:
            self._hdfs_ha_update_host_component(hac, jn,
                                                'JOURNALNODE', 'STARTED')

        # disable any secondary namnodes
        for snn in hac['snn_hosts']:
            self._hdfs_ha_update_host_component(hac, snn,
                                                'SECONDARY_NAMENODE',
                                                'DISABLED')

        # get hdfs-site config tag
        hdfs_site_tag = self._hdfs_ha_get_config_tag(hac, 'hdfs-site')

        # get hdfs-site config
        hdfs_site = self._hdfs_ha_get_config(hac, 'hdfs-site', hdfs_site_tag)

        # update hdfs-site with HDFS HA properties
        hdfs_site_ha = self._hdfs_ha_update_hdfs_site(hac, hdfs_site)

        # put new hdfs-site config
        self._hdfs_ha_put_config(hac, 'hdfs-site', hac['config_ver'],
                                 hdfs_site_ha)

        # get core-site tag
        core_site_tag = self._hdfs_ha_get_config_tag(hac, 'core-site')

        # get core-site config
        core_site = self._hdfs_ha_get_config(hac, 'core-site', core_site_tag)

        # update core-site with HDFS HA properties
        core_site_ha = self._hdfs_ha_update_core_site(hac, core_site)

        # put new HA core-site config
        self._hdfs_ha_put_config(hac, 'core-site', hac['config_ver'],
                                 core_site_ha)

        # update hbase-site if Hbase is installed
        if hac['hbase_hosts']:
            hbase_site_tag = self._hdfs_ha_get_config_tag(hac, 'hbase-site')
            hbase_site = self._hdfs_ha_get_config(hac, 'hbase-site',
                                                  hbase_site_tag)
            hbase_site_ha = self._hdfs_ha_update_hbase_site(hac, hbase_site)
            self._hdfs_ha_put_config(hac, 'hbase_site', hac['config_ver'],
                                     hbase_site_ha)

        # force the deployment of HDFS HA configs on namenodes by re-installing
        # hdfs-client
        self._hdfs_ha_update_host_component(hac, hac['nn_active'],
                                            'HDFS_CLIENT', 'INSTALLED')
        self._hdfs_ha_update_host_component(hac, hac['nn_standby'],
                                            'HDFS_CLIENT', 'INSTALLED')

        # initialize shared edits on the active namenode
        hac['server_active'].initialize_shared_edits(hac['java_home'])

        # start zookeeper servers
        for zk in hac['zk_hosts']:
            self._hdfs_ha_update_host_component(hac, zk,
                                                'ZOOKEEPER_SERVER', 'STARTED')

        # start active namenode
        self._hdfs_ha_update_host_component(hac, hac['nn_active'],
                                            'NAMENODE', 'STARTED')

        # setup active namenode automatic failover
        hac['server_active'].format_zookeeper_fc(hac['java_home'])

        # format standby namenode
        hac['server_standby'].bootstrap_standby_namenode(hac['java_home'])

        # start namenode process on standby namenode
        self._hdfs_ha_update_host_component(hac, hac['nn_standby'],
                                            'NAMENODE', 'STARTED')

        # add, install and start ZKFC on namenodes for automatic fail-over
        for nn in hac['nn_hosts']:
            self._hdfs_ha_add_host_component(hac, nn, 'ZKFC')
            self._hdfs_ha_update_host_component(hac, nn, 'ZKFC', 'INSTALLED')
            self._hdfs_ha_update_host_component(hac, nn, 'ZKFC', 'STARTED')

        # delete any secondary namenodes
        for snn in hac['snn_hosts']:
            self._hdfs_ha_delete_host_component(hac, snn, 'SECONDARY_NAMENODE')

        # stop journalnodes and namenodes before terminating
        # not doing so causes warnings in Ambari for stale config
        for jn in hac['jn_hosts']:
            self._hdfs_ha_update_host_component(hac, jn, 'JOURNALNODE',
                                                'INSTALLED')
        for nn in hac['nn_hosts']:
            self._hdfs_ha_update_host_component(hac, nn, 'NAMENODE',
                                                'INSTALLED')

        # install httpfs and write temp file if HUE is installed
        if hac['hue_host']:
            self._hdfs_ha_setup_hue(hac)

    def _hdfs_ha_cluster_map(self, cluster_spec, servers, ambari_info, name):

        hacluster = {}

        hacluster['name'] = name

        hacluster['config_ver'] = 'v2'

        # set JAVA_HOME
        global_config = cluster_spec.configurations.get('global', None)
        global_config_jh = (global_config.get('java64_home', None) or
                            global_config.get('java_home', None) if
                            global_config else None)
        hacluster['java_home'] = global_config_jh or '/opt/jdk1.6.0_31'

        # set namnode ports
        hacluster['nn_rpc'] = '8020'
        hacluster['nn_ui'] = '50070'

        hacluster['ambari_info'] = ambari_info

        # get host lists
        hacluster['nn_hosts'] = [x.fqdn().lower() for x in
                                 cluster_spec.determine_component_hosts(
                                     'NAMENODE')]
        hacluster['snn_hosts'] = [x.fqdn().lower() for x in
                                  cluster_spec.determine_component_hosts(
                                      'SECONDARY_NAMENODE')]
        hacluster['jn_hosts'] = [x.fqdn().lower() for x in
                                 cluster_spec.determine_component_hosts(
                                     'JOURNALNODE')]
        hacluster['zk_hosts'] = [x.fqdn().lower() for x in
                                 cluster_spec.determine_component_hosts(
                                     'ZOOKEEPER_SERVER')]
        hacluster['hdfsc_hosts'] = [x.fqdn().lower() for x in
                                    cluster_spec.determine_component_hosts(
                                        'HDFS_CLIENT')]
        hacluster['hbase_hosts'] = [x.fqdn().lower() for x in
                                    cluster_spec.determine_component_hosts(
                                        'HBASE_MASTER')]
        hacluster['hue_host'] = [x.fqdn().lower() for x in
                                 cluster_spec.determine_component_hosts('HUE')]

        # get servers for remote command execution
        # consider hacluster['nn_hosts'][0] as active namenode
        hacluster['nn_active'] = hacluster['nn_hosts'][0]
        hacluster['nn_standby'] = hacluster['nn_hosts'][1]
        # get the 2 namenode servers and hue server
        for server in servers:
            if server.instance.fqdn().lower() == hacluster['nn_active']:
                hacluster['server_active'] = server
            if server.instance.fqdn().lower() == hacluster['nn_standby']:
                hacluster['server_standby'] = server
            if hacluster['hue_host']:
                if server.instance.fqdn().lower() == hacluster['hue_host'][0]:
                    hacluster['server_hue'] = server

        return hacluster

    def _hdfs_ha_delete_host_component(self, hac, host, component):

        delete_service_component_url = ('http://{0}/api/v1/clusters/{1}/hosts'
                                        '/{2}/host_components/{3}').format(
                                            hac['ambari_info'].get_address(),
                                            hac['name'], host, component)

        result = self._delete(delete_service_component_url, hac['ambari_info'])
        if result.status_code != 200:
            LOG.error(_LE('Configuring HDFS HA failed. {result}').format(
                result=result.text))
            raise ex.NameNodeHAConfigurationError(
                'Configuring HDFS HA failed. %s' % result.text)

    def _hdfs_ha_add_host_component(self, hac, host, component):
        add_host_component_url = ('http://{0}/api/v1/clusters/{1}'
                                  '/hosts/{2}/host_components/{3}').format(
                                      hac['ambari_info'].get_address(),
                                      hac['name'], host, component)

        result = self._post(add_host_component_url, hac['ambari_info'])
        if result.status_code != 201:
            LOG.error(_LE('Configuring HDFS HA failed. {result}').format(
                result=result.text))
            raise ex.NameNodeHAConfigurationError(
                'Configuring HDFS HA failed. %s' % result.text)

    def _hdfs_ha_update_host_component(self, hac, host, component, state):

        update_host_component_url = ('http://{0}/api/v1/clusters/{1}'
                                     '/hosts/{2}/host_components/{3}').format(
                                         hac['ambari_info'].get_address(),
                                         hac['name'], host, component)
        component_state = {"HostRoles": {"state": state}}
        body = json.dumps(component_state)

        result = self._put(update_host_component_url,
                           hac['ambari_info'], data=body)

        if result.status_code == 202:
            json_result = json.loads(result.text)
            request_id = json_result['Requests']['id']
            success = self._wait_for_async_request(self._get_async_request_uri(
                hac['ambari_info'], hac['name'], request_id),
                hac['ambari_info'])
            if success:
                LOG.info(_LI("HDFS-HA: Host component updated successfully: "
                             "{host} {component}").format(host=host,
                                                          component=component))
            else:
                LOG.error(_LE("HDFS-HA: Host component update failed: "
                              "{host} {component}").format(
                                  host=host, component=component))
                raise ex.NameNodeHAConfigurationError(
                    'Configuring HDFS HA failed. %s' % result.text)
        elif result.status_code != 200:
            LOG.error(
                _LE('Configuring HDFS HA failed. {result}').format(
                    result=result.text))
            raise ex.NameNodeHAConfigurationError(
                'Configuring HDFS HA failed. %s' % result.text)

    def _hdfs_ha_get_config_tag(self, hac, config_name):

        config_url = ('http://{0}/api/v1/clusters/{1}'
                      '/configurations?type={2}').format(
                          hac['ambari_info'].get_address(), hac['name'],
                          config_name)

        result = self._get(config_url, hac['ambari_info'])
        if result.status_code == 200:
            json_result = json.loads(result.text)
            items = json_result['items']
            return items[0]['tag']
        else:
            LOG.error(
                _LE('Configuring HDFS HA failed. {result}').format(
                    result=result.text))
            raise ex.NameNodeHAConfigurationError(
                'Configuring HDFS HA failed. %s' % result.text)

    def _hdfs_ha_get_config(self, hac, config_name, tag):

        config_url = ('http://{0}/api/v1/clusters/{1}'
                      '/configurations?type={2}&tag={3}').format(
                          hac['ambari_info'].get_address(), hac['name'],
                          config_name, tag)

        result = self._get(config_url, hac['ambari_info'])
        if result.status_code == 200:
            json_result = json.loads(result.text)
            items = json_result['items']
            return items[0]['properties']
        else:
            LOG.error(
                _LE('Configuring HDFS HA failed. {result}').format(
                    result=result.text))
            raise ex.NameNodeHAConfigurationError(
                'Configuring HDFS HA failed. %s' % result.text)

    def _hdfs_ha_put_config(self, hac, config_name, tag, properties):

        config_url = ('http://{0}/api/v1/clusters/{1}').format(
            hac['ambari_info'].get_address(), hac['name'])

        body = {}
        clusters = {}
        body['Clusters'] = clusters
        body['Clusters']['desired_config'] = {}
        body['Clusters']['desired_config']['type'] = config_name
        body['Clusters']['desired_config']['tag'] = tag
        body['Clusters']['desired_config']['properties'] = properties

        LOG.debug("body: {body}".format(body=body))

        result = self._put(config_url, hac['ambari_info'],
                           data=json.dumps(body))
        if result.status_code != 200:
            LOG.error(
                _LE('Configuring HDFS HA failed. {result}').format(
                    result=result.text))
            raise ex.NameNodeHAConfigurationError(
                'Configuring HDFS HA failed. %s' % result.text)

    def _hdfs_ha_update_hdfs_site(self, hac, hdfs_site):

        hdfs_site['dfs.nameservices'] = hac['name']

        hdfs_site['dfs.ha.namenodes.{0}'.format(
            hac['name'])] = hac['nn_active'] + ',' + hac['nn_standby']

        hdfs_site['dfs.namenode.rpc-address.{0}.{1}'.format(
            hac['name'], hac['nn_active'])] = '{0}:{1}'.format(
                hac['nn_active'], hac['nn_rpc'])
        hdfs_site['dfs.namenode.rpc-address.{0}.{1}'.format(
            hac['name'], hac['nn_standby'])] = '{0}:{1}'.format(
                hac['nn_standby'], hac['nn_rpc'])
        hdfs_site['dfs.namenode.http-address.{0}.{1}'.format(
            hac['name'], hac['nn_active'])] = '{0}:{1}'.format(
                hac['nn_active'], hac['nn_ui'])
        hdfs_site['dfs.namenode.http-address.{0}.{1}'.format(
            hac['name'], hac['nn_standby'])] = '{0}:{1}'.format(
                hac['nn_standby'], hac['nn_ui'])

        qjournal = ';'.join([x+':8485' for x in hac['jn_hosts']])
        hdfs_site['dfs.namenode.shared.edits.dir'] = ('qjournal://{0}/{1}'.
                                                      format(qjournal,
                                                             hac['name']))

        hdfs_site['dfs.client.failover.proxy.provider.{0}'.format(
            hac['name'])] = ("org.apache.hadoop.hdfs.server.namenode.ha."
                             "ConfiguredFailoverProxyProvider")

        hdfs_site['dfs.ha.fencing.methods'] = 'shell(/bin/true)'

        hdfs_site['dfs.ha.automatic-failover.enabled'] = 'true'

        return hdfs_site

    def _hdfs_ha_update_core_site(self, hac, core_site):

        core_site['fs.defaultFS'] = 'hdfs://{0}'.format(hac['name'])
        core_site['ha.zookeeper.quorum'] = '{0}'.format(
            ','.join([x+':2181' for x in hac['zk_hosts']]))

        # if HUE is installed add some httpfs configs
        if hac['hue_host']:
            core_site['hadoop.proxyuser.httpfs.groups'] = '*'
            core_site['hadoop.proxyuser.httpfs.hosts'] = '*'

        return core_site

    def _hdfs_ha_update_hbase_site(self, hac, hbase_site):

        hbase_site['hbase.rootdir'] = 'hdfs://{0}/apps/hbase/data'.format(
            hac['name'])
        return hbase_site

    def _hdfs_ha_setup_hue(self, hac):

        hac['server_hue'].install_httpfs()

        # write a temp file and
        # use it when starting HUE with HDFS HA enabled
        hac['server_hue'].write_hue_temp_file('/tmp/hueini-hdfsha',
                                              hac['name'])
