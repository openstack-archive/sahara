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

from oslo_config import cfg
from oslo_log import log as logging
import pkg_resources as pkg

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
from sahara.plugins.hdp.versions.version_1_3_2 import edp_engine
from sahara.plugins.hdp.versions.version_1_3_2 import services
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
                          'plugins/hdp/versions/version_1_3_2/resources/'
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
            cluster_spec = cs.ClusterSpec(cluster_template)
        else:
            if scaled_groups:
                for ng in cluster.node_groups:
                    ng_id = ng['id']
                    if (ng_id in scaled_groups and
                       ng['count'] > scaled_groups[ng_id]):
                            raise ex.ClusterCannotBeScaled(
                                cluster.name,
                                _('The HDP plugin does not support '
                                  'the decommissioning of nodes '
                                  'for HDP version 1.3.2'))

            cluster_spec = self.get_default_cluster_configuration()
            cluster_spec.create_operational_config(
                cluster, user_inputs, scaled_groups)

            cs.validate_number_of_datanodes(
                cluster, scaled_groups, self.get_config_items())

        return cluster_spec

    def get_default_cluster_configuration(self):
        return cs.ClusterSpec(self._get_default_cluster_template())

    def _get_default_cluster_template(self):
        return pkg.resource_string(
            version.version_info.package,
            'plugins/hdp/versions/version_1_3_2/resources/'
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
            'DATANODE': [50075, 50475, 50010, 50020],
            'SECONDARY_NAMENODE': [50090],
            'JOBTRACKER': [50030, 8021],
            'TASKTRACKER': [50060],
            'HISTORYSERVER': [51111],
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
        if data:
            LOG.debug('AmbariClient:_post call, url = {url} data = {data}'
                      .format(url=url, data=str(data)))
        else:
            LOG.debug('AmbariClient:_post call, url = {url}'.format(url=url))

        session = self._get_http_session(ambari_info.host, ambari_info.port)
        return session.post(url, data=data,
                            auth=(ambari_info.user, ambari_info.password),
                            headers=self._get_standard_headers())

    def _delete(self, url, ambari_info):
        LOG.debug('AmbariClient:_delete call, url = {url}'.format(url=url))
        session = self._get_http_session(ambari_info.host, ambari_info.port)
        return session.delete(url,
                              auth=(ambari_info.user, ambari_info.password),
                              headers=self._get_standard_headers())

    def _put(self, url, ambari_info, data=None):
        if data:
            LOG.debug('AmbariClient:_put call, url = {url} data = {data}'
                      .format(url=url, data=str(data)))
        else:
            LOG.debug('AmbariClient:_put call, url = {url}'.format(url=url))

        session = self._get_http_session(ambari_info.host, ambari_info.port)
        auth = (ambari_info.user, ambari_info.password)
        return session.put(url, data=data, auth=auth,
                           headers=self._get_standard_headers())

    def _get(self, url, ambari_info):
        LOG.debug('AmbariClient:_get call, url = {url}'.format(url=url))
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
                    existing_version = (
                        existing_configs[config_name]['tag'].lstrip('v'))
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
            if service.deployed and service.name != 'AMBARI':
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
            if service.deployed and service.name != 'AMBARI':
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
                # don't add any AMBARI components
                if component.find('AMBARI') != 0:
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
                LOG.info(_LI("Hadoop stack installed successfully."))
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

    def _wait_for_async_request(self, request_url, ambari_info):
        started = False
        while not started:
            result = self._get(request_url, ambari_info)
            LOG.debug(
                'async request {url} response: {response}'.format(
                    url=request_url, response=result.text))
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

        persist_state_uri = 'http://{0}/api/v1/persist'.format(
            ambari_info.get_address())
        # this post data has non-standard format because persist
        # resource doesn't comply with Ambari API standards
        persist_data = ('{ "CLUSTER_CURRENT_STATUS":'
                        '"{\\"clusterState\\":\\"CLUSTER_STARTED_5\\"}" }')
        result = self._post(persist_state_uri, ambari_info, data=persist_data)

        if result.status_code != 201 and result.status_code != 202:
            LOG.warning(_LW('Finalizing of Ambari cluster state failed. '
                            '{result}').format(result.text))
            raise ex.HadoopProvisionError(_('Unable to finalize Ambari '
                                            'state.'))
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
                LOG.info(_LI('Cluster name: {cluster_name}, '
                             'Ambari server address: {server_address}')
                         .format(cluster_name=cluster_name,
                                 server_address=ambari_info.get_address()))
            else:
                LOG.error(_LE('Failed to start Hadoop cluster.'))
                raise ex.HadoopProvisionError(
                    _('Start of Hadoop services failed.'))

        elif result.status_code != 200:
            LOG.error(
                _LE('Start command failed. Status: {status}, '
                    'response: {response}').format(status=result.status_code,
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

            LOG.debug('Registered Hosts: {current_number} '
                      'of {final_number}'.format(
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
                       format(user.password, '%s' %
                                             ','.join(map(str, user.groups))))

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
        raise exc.InvalidDataException(_('The HDP plugin does not support '
                                         'the decommissioning of nodes '
                                         'for HDP version 1.3.2'))

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
            LOG.warning(_LW("HTTP session is not cached"))

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
