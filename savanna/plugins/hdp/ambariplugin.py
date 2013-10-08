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

from savanna import conductor
from savanna import context
from savanna import exceptions as exc
from savanna.openstack.common import jsonutils as json
from savanna.openstack.common import log as logging
from savanna.plugins.hdp import exceptions as ex
from savanna.plugins.hdp import hadoopserver as h
from savanna.plugins.hdp import savannautils as utils
from savanna.plugins.hdp import validator as v
from savanna.plugins.hdp.versions import versionhandlerfactory as vhf
from savanna.plugins import provisioning as p


conductor = conductor.API
LOG = logging.getLogger(__name__)


class AmbariPlugin(p.ProvisioningPluginBase):
    def __init__(self):
        self.cluster_ambari_mapping = {}
        self.version_factory = vhf.VersionHandlerFactory.get_instance()

    def create_cluster(self, cluster, cluster_template):

        if cluster_template is None:
            raise ValueError('must supply cluster template')

        version = cluster.hadoop_version
        handler = self.version_factory.get_version_handler(version)

        cluster_spec = handler.get_cluster_spec(cluster_template, cluster)

        hosts = self._get_servers(cluster)
        ambari_info = self.get_ambari_info(cluster_spec)
        self.cluster_ambari_mapping[cluster.name] = ambari_info
        rpm = self._get_rpm_uri(cluster_spec)

        servers = []
        for host in hosts:
            host_role = utils.get_host_role(host)
            servers.append(
                h.HadoopServer(host, cluster_spec.node_groups[host_role],
                               ambari_rpm=rpm))

        provisioned = self._provision_cluster(
            cluster.name, cluster_spec, ambari_info, servers,
            cluster.hadoop_version)

        if provisioned:
            LOG.info("Install of Hadoop stack successful.")
            # add service urls
            self._set_cluster_info(cluster, cluster_spec, ambari_info)
        else:
            raise ex.HadoopProvisionError(
                'Installation of Hadoop stack failed.')

    def _get_servers(self, cluster):
        servers = []
        if hasattr(cluster, 'node_groups') and cluster.node_groups is not None:
            # code for a savanna cluster object
            for node_group in cluster.node_groups:
                servers += node_group.instances
        else:
            # cluster is actually a cloud context
            servers = cluster.instances

        return servers

    def get_node_processes(self, hadoop_version):
        node_processes = {}
        version_handler = \
            self.version_factory.get_version_handler(hadoop_version)
        default_config = version_handler.get_default_cluster_configuration()
        for service in default_config.services:
            components = []
            for component in service.components:
                components.append(component.name)
            node_processes[service.name] = components

        return node_processes

    def convert(self, config, plugin_name, version, template_name,
                cluster_template_create):
        handler = self.version_factory.get_version_handler(version)
        normalized_config = handler.get_cluster_spec(config, None).normalize()

        #TODO(jspeidel):  can we get the name (first arg) from somewhere?

        node_groups = []
        for ng in normalized_config.node_groups:
            node_group = {
                "name": ng.name,
                "flavor_id": ng.flavor,
                "node_processes": ng.node_processes,
                "count": ng.count
            }
            node_groups.append(node_group)

        cluster_configs = dict()
        config_resource = handler.get_config_items()
        for entry in normalized_config.cluster_configs:
            user_input = next((ui for ui in config_resource
                               if entry.config.name == ui.name), None)
            if user_input is not None:
                ci = entry.config
                # get the associated service dictionary
                target = entry.config.applicable_target
                service_dict = cluster_configs.get(target, {})
                service_dict[ci.name] = entry.value
                cluster_configs[target] = service_dict
            else:
                LOG.debug('Template based input "{0}" is being filtered out as'
                          ' it is not considered a user input'
                          .format(entry.config.name))

        ctx = context.ctx()
        return cluster_template_create(ctx,
                                       {"name": template_name,
                                        "plugin_name": plugin_name,
                                        "hadoop_version": version,
                                        "node_groups": node_groups,
                                        "cluster_configs": cluster_configs})

    def update_infra(self, cluster):
        pass

    def convert_props_to_template(self, props):
        raise NotImplementedError('not yet supported')

    def _spawn(self, description, func, *args, **kwargs):
        context.spawn(description, func, *args, **kwargs)

    def _provision_cluster(self, name, cluster_spec, ambari_info, servers,
                           version):
        #TODO(jspeidel): encapsulate in another class

        LOG.info('Provisioning Cluster via Ambari Server: {0} ...'.format(
            ambari_info.get_address()))

        for server in servers:
            self._spawn(
                "hdp-provision-instance-%s" % server.instance.hostname,
                server.provision_ambari, ambari_info)

        handler = self.version_factory.get_version_handler(version)
        ambari_client = handler.get_ambari_client()

        ambari_client.wait_for_host_registrations(len(servers), ambari_info)

        self._set_ambari_credentials(cluster_spec, ambari_info, version)

        if not ambari_client.provision_cluster(cluster_spec, servers,
                                               ambari_info, name):
            return False

        return True

    def _set_cluster_info(self, cluster, cluster_spec, ambari_info):
        info = {}

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

        ctx = context.ctx()
        conductor.cluster_update(ctx, cluster, {'info': info})

    def _set_ambari_credentials(self, cluster_spec, ambari_info, version):
        services = cluster_spec.services
        ambari_client = self.version_factory.get_version_handler(version).\
            get_ambari_client()
        for service in services:
            if service.name == 'AMBARI':
                is_admin_provided = False
                admin_user = ambari_info.user
                admin_password = ambari_info.password
                for u in service.users:
                    if u.name == 'admin':
                        ambari_client.update_ambari_admin_user(
                            u.password, ambari_info)
                        is_admin_provided = True
                        ambari_info.user = 'admin'
                        ambari_info.password = u.password
                    else:
                        ambari_client.add_ambari_user(u, ambari_info)
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
                    ambari_client.delete_ambari_user('admin', ambari_info)
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

    # SAVANNA PLUGIN SPI METHODS:
    def _get_blueprint_processor(self, cluster):
        version = cluster.hadoop_version
        handler = self.version_factory.get_version_handler(version)
        user_inputs = self._map_to_user_inputs(version,
                                               cluster.cluster_configs)
        processor = handler.process_cluster(user_inputs, cluster.node_groups)
        return processor

    def configure_cluster(self, cluster):
        # take the user inputs from the cluster and node groups and convert
        # to a ambari blueprint
        processor = self._get_blueprint_processor(cluster)
        # NOTE: for the time being we are going to ignore the node group
        # level configurations.  we are not currently
        # defining node level configuration items (i.e. scope='cluster' in
        # all cases for returned configs)

        self.create_cluster(cluster, json.dumps(processor.blueprint))

    def get_versions(self):
        return self.version_factory.get_versions()

    def get_configs(self, hadoop_version):
        handler = self.version_factory.get_version_handler(hadoop_version)
        return handler.get_config_items()

    # cluster name argument supports the non-savanna cluster creation mode
    def start_cluster(self, cluster, cluster_name=None):
        if cluster_name is None:
            cluster_name = cluster.name

        client = self.version_factory.get_version_handler(
            cluster.hadoop_version).get_ambari_client()

        client.start_services(
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
        handler = self.version_factory.get_version_handler(
            cluster.hadoop_version)
        ambari_client = handler.get_ambari_client()
        processor = self._get_blueprint_processor(cluster)
        cluster_spec = handler.get_cluster_spec(
            json.dumps(processor.blueprint), cluster)
        rpm = self._get_rpm_uri(cluster_spec)

        servers = []
        for instance in instances:
            host_role = utils.get_host_role(instance)
            servers.append(h.HadoopServer(instance,
                                          cluster_spec.node_groups
                                          [host_role],
                                          ambari_rpm=rpm))

        ambari_info = self.get_ambari_info(cluster_spec)
        self._update_ambari_info_credentials(cluster_spec, ambari_info)

        for server in servers:
            self._spawn('Ambari provisioning thread',
                        server.provision_ambari, ambari_info)

        ambari_client.scale_cluster(cluster.name, cluster_spec, servers,
                                    self._get_num_hosts(cluster), ambari_info)

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

    def _get_rpm_uri(self, cluster_spec):
        ambari_config = cluster_spec.configurations['ambari']
        return ambari_config.get('rpm', None)

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
