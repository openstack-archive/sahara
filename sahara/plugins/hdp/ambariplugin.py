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

from oslo_config import cfg
from oslo_log import log as logging

from sahara import conductor as c
from sahara import context
from sahara import exceptions as base_exc
from sahara.i18n import _
from sahara.i18n import _LI
from sahara.plugins import exceptions as ex
from sahara.plugins.hdp import hadoopserver as h
from sahara.plugins.hdp import saharautils as utils
from sahara.plugins.hdp.versions import versionhandlerfactory as vhf
from sahara.plugins import provisioning as p
from sahara.topology import topology_helper as th
from sahara.utils import cluster_progress_ops as cpo


conductor = c.API
LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class AmbariPlugin(p.ProvisioningPluginBase):
    def __init__(self):
        self.cluster_ambari_mapping = {}
        self.version_factory = vhf.VersionHandlerFactory.get_instance()

    def create_cluster(self, cluster):
        version = cluster.hadoop_version
        handler = self.version_factory.get_version_handler(version)

        cluster_spec = handler.get_cluster_spec(
            cluster, self._map_to_user_inputs(
                version, cluster.cluster_configs))
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

        self._provision_cluster(
            cluster.name, cluster_spec, ambari_info, servers,
            cluster.hadoop_version)

        # add the topology data file and script if rack awareness is
        # enabled
        self._configure_topology_for_cluster(cluster, servers)

        LOG.info(_LI("Install of Hadoop stack successful."))
        # add service urls
        self._set_cluster_info(cluster, cluster_spec)

        # check if HDFS HA is enabled; set it up if so
        if cluster_spec.is_hdfs_ha_enabled(cluster):
            self.configure_hdfs_ha(cluster)

    @cpo.event_wrapper(
        True, step=_("Add configurations to cluster"), param=('cluster', 1))
    def configure_hdfs_ha(self, cluster):
        LOG.debug("Configuring HDFS HA")
        version = cluster.hadoop_version
        handler = self.version_factory.get_version_handler(version)

        cluster_spec = handler.get_cluster_spec(
            cluster, self._map_to_user_inputs(
                version, cluster.cluster_configs))
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

        ambari_client = handler.get_ambari_client()
        ambari_client.setup_hdfs_ha(cluster_spec, servers, ambari_info,
                                    cluster.name)
        LOG.info(_LI("Configure HDFS HA successful."))

    def _get_servers(self, cluster):
        servers = []
        if hasattr(cluster, 'node_groups') and cluster.node_groups is not None:
            # code for a cluster object
            for node_group in cluster.node_groups:
                servers += node_group.instances
        else:
            # cluster is actually a cloud context
            servers = cluster.instances

        return servers

    def get_node_processes(self, hadoop_version):
        node_processes = {}
        version_handler = (
            self.version_factory.get_version_handler(hadoop_version))
        default_config = version_handler.get_default_cluster_configuration()
        for service in default_config.services:
            components = []
            for component in service.components:
                if service.is_user_template_component(component):
                    components.append(component.name)
            node_processes[service.name] = components

        return node_processes

    def convert(self, config, plugin_name, version, template_name,
                cluster_template_create):
        handler = self.version_factory.get_version_handler(version)
        normalized_config = handler.get_cluster_spec(
            None, None, cluster_template=config).normalize()

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
                LOG.debug('Template based input "{entry_name}" is being'
                          ' filtered out as it is not considered a user input'
                          .format(entry_name=entry.config.name))

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

    def _provision_cluster(self, name, cluster_spec, ambari_info,
                           servers, version):
        # TODO(jspeidel): encapsulate in another class

        if servers:
            cpo.add_provisioning_step(
                servers[0].cluster_id,
                _("Provision cluster via Ambari"), len(servers))

        with context.ThreadGroup() as tg:
            for server in servers:
                with context.set_current_instance_id(
                        server.instance['instance_id']):
                    tg.spawn(
                        "hdp-provision-instance-%s" %
                        server.instance.hostname(),
                        server.provision_ambari, ambari_info, cluster_spec)

        handler = self.version_factory.get_version_handler(version)
        ambari_client = handler.get_ambari_client()

        ambari_client.wait_for_host_registrations(len(servers), ambari_info)
        self._set_ambari_credentials(cluster_spec, ambari_info, version)

        ambari_client.provision_cluster(
            cluster_spec, servers, ambari_info, name)

        LOG.info(_LI('Cluster provisioned via Ambari Server: {server_ip}')
                 .format(server_ip=ambari_info.get_address()))

    # TODO(jspeidel): invoke during scale cluster.  Will need to handle dups
    def _set_cluster_info(self, cluster, cluster_spec):
        info = {}
        for service in cluster_spec.services:
            if service.deployed:
                service.register_service_urls(cluster_spec, info, cluster)

        conductor.cluster_update(context.ctx(), cluster, {'info': info})

    def _set_ambari_credentials(self, cluster_spec, ambari_info, version):
        services = cluster_spec.services
        ambari_client = (self.version_factory.get_version_handler(version).
                         get_ambari_client())
        for service in services:
            if service.name == 'AMBARI':
                is_admin_provided = False
                admin_user = ambari_info.user
                admin_password = ambari_info.password
                for user in service.users:
                    if user.name == 'admin':
                        ambari_client.update_ambari_admin_user(
                            user.password, ambari_info)
                        is_admin_provided = True
                        ambari_info.user = 'admin'
                        ambari_info.password = user.password
                    else:
                        ambari_client.add_ambari_user(user, ambari_info)
                        if 'admin' in user.groups:
                            admin_user = user.name
                            admin_password = user.password

                if not is_admin_provided:
                    if admin_user is None:
                        raise ex.HadoopProvisionError(_("An Ambari user in the"
                                                        " admin group must be "
                                                        "configured."))
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

        LOG.info(_LI('Using "{username}" as admin user for scaling of cluster')
                 .format(username=ambari_info.user))

    # PLUGIN SPI METHODS:
    def get_versions(self):
        return self.version_factory.get_versions()

    def configure_cluster(self, cluster):
        self.create_cluster(cluster)

    def get_configs(self, hadoop_version):
        handler = self.version_factory.get_version_handler(hadoop_version)
        return handler.get_config_items()

    # cluster name argument supports the non-sahara cluster creation mode
    def start_cluster(self, cluster):
        client = self.version_factory.get_version_handler(
            cluster.hadoop_version).get_ambari_client()

        handler = self.version_factory.get_version_handler(
            cluster.hadoop_version)

        cluster_spec = handler.get_cluster_spec(
            cluster, self._map_to_user_inputs(
                cluster.hadoop_version, cluster.cluster_configs))

        try:
            client.start_services(cluster.name, cluster_spec,
                                  self.cluster_ambari_mapping[cluster.name])
        finally:
            client.cleanup(self.cluster_ambari_mapping[cluster.name])

    def get_title(self):
        return 'Hortonworks Data Platform'

    def get_description(self):
        return _('The Hortonworks Sahara plugin automates the deployment '
                 'of the Hortonworks Data Platform (HDP) on OpenStack.')

    def validate(self, cluster):
        raise base_exc.DeprecatedException(
            _("The HDP 2.0.6 plugin is deprecated in Mitaka release and "
              "will be removed in Newton release. Please, use the Ambari 2.3 "
              "instead."))

    def scale_cluster(self, cluster, instances):
        handler = self.version_factory.get_version_handler(
            cluster.hadoop_version)
        ambari_client = handler.get_ambari_client()
        cluster_spec = handler.get_cluster_spec(
            cluster, self._map_to_user_inputs(
                cluster.hadoop_version, cluster.cluster_configs))
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

        cpo.add_provisioning_step(
            cluster.id, _("Provision cluster via Ambari"), len(servers))

        with context.ThreadGroup() as tg:
            for server in servers:
                with context.set_current_instance_id(
                        server.instance['instance_id']):
                    tg.spawn('Ambari provisioning thread',
                             server.provision_ambari,
                             ambari_info, cluster_spec)

        ambari_client.configure_scaled_cluster_instances(
            cluster.name, cluster_spec, self._get_num_hosts(cluster),
            ambari_info)
        self._configure_topology_for_cluster(cluster, servers)
        ambari_client.start_scaled_cluster_instances(cluster.name,
                                                     cluster_spec, servers,
                                                     ambari_info)

        ambari_client.cleanup(ambari_info)

    def get_edp_engine(self, cluster, job_type):
        version_handler = (
            self.version_factory.get_version_handler(cluster.hadoop_version))
        return version_handler.get_edp_engine(cluster, job_type)

    def get_edp_job_types(self, versions=None):
        res = {}
        for vers in self.version_factory.get_versions():
            if not versions or vers in versions:
                vh = self.version_factory.get_version_handler(vers)
                res[vers] = vh.get_edp_job_types()
        return res

    def get_edp_config_hints(self, job_type, version):
        version_handler = (
            self.version_factory.get_version_handler(version))
        return version_handler.get_edp_config_hints(job_type)

    def decommission_nodes(self, cluster, instances):
        LOG.info(_LI('AmbariPlugin: decommission_nodes called for '
                 'HDP version = {version}')
                 .format(version=cluster.hadoop_version))

        handler = self.version_factory.get_version_handler(
            cluster.hadoop_version)
        ambari_client = handler.get_ambari_client()
        cluster_spec = handler.get_cluster_spec(
            cluster, self._map_to_user_inputs(
                cluster.hadoop_version, cluster.cluster_configs))

        ambari_info = self.get_ambari_info(cluster_spec)
        ambari_client.decommission_cluster_instances(cluster, cluster_spec,
                                                     instances,
                                                     ambari_info)

    def validate_scaling(self, cluster, existing, additional):
        handler = self.version_factory.get_version_handler(
            cluster.hadoop_version)

        # results in validation
        handler.get_cluster_spec(
            cluster, [],
            dict(list(existing.items()) + list(additional.items())))

    def _get_num_hosts(self, cluster):
        count = 0
        for node_group in cluster.node_groups:
            count += node_group.count

        return count

    def _get_host_list(self, servers):
        host_list = [server.instance.fqdn().lower() for server in servers]
        return ",".join(host_list)

    def _get_rpm_uri(self, cluster_spec):
        ambari_config = cluster_spec.configurations['ambari']
        return ambari_config.get('rpm', None)

    def get_ambari_info(self, cluster_spec):
        ambari_host = cluster_spec.determine_component_hosts(
            'AMBARI_SERVER').pop()

        port = cluster_spec.configurations['ambari'].get(
            'server.port', '8080')

        return AmbariInfo(ambari_host, port, 'admin', 'admin')

    def _configure_topology_for_cluster(self, cluster, servers):
        if CONF.enable_data_locality:
            cpo.add_provisioning_step(
                cluster.id, _("Enable data locality for cluster"),
                len(servers))
            topology_data = th.generate_topology_map(
                cluster, CONF.enable_hypervisor_awareness)
            topology_str = "\n".join(
                [k + " " + v for k, v in topology_data.items()]) + "\n"
            for server in servers:
                server.configure_topology(topology_str)

    def get_open_ports(self, node_group):
        handler = self.version_factory.get_version_handler(
            node_group.cluster.hadoop_version)
        return handler.get_open_ports(node_group)


class AmbariInfo(object):
    def __init__(self, host, port, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def get_address(self):
        return '{0}:{1}'.format(self.host.management_ip, self.port)

    def is_ambari_info(self):
        pass

    def get_cluster(self):
        sahara_instance = self.host.sahara_instance
        return sahara_instance.cluster

    def get_event_info(self):
        return self.host.sahara_instance
