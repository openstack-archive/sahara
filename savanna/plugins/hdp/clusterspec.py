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
from savanna.openstack.common import jsonutils as json
from savanna.openstack.common import log as logging
from savanna.plugins.hdp import configprovider as cfg
from savanna.plugins.hdp import savannautils as utils

LOG = logging.getLogger(__name__)


class ClusterSpec():
    def __init__(self, cluster_template, cluster=None):
        self.services = []
        self.configurations = {}
        self.node_groups = {}
        self.servers = None
        self.str = cluster_template

        if cluster:
            self.servers = self._get_servers_from_savanna_cluster(cluster)
            host_manifest = self._generate_host_manifest()
            cluster_template = self._replace_config_tokens(cluster_template)

            self.str = self._add_manifest_to_config(
                cluster_template, host_manifest)

        template_json = json.loads(self.str)
        self._parse_services(template_json)
        self._parse_configurations(template_json)
        self._parse_host_component_mappings(template_json)

    def determine_host_for_server_component(self, component):
        host = None
        for server in self.servers:
            node_processes = utils.get_node_processes(server)
            if node_processes is not None and component in node_processes:
                host = server
                break

        return host

    def normalize(self):
        return NormalizedClusterConfig(self)

    def _get_servers_from_savanna_cluster(self, cluster):
        servers = []
        for node_group in cluster.node_groups:
            for server in node_group.instances:
                setattr(server, 'role', node_group.name)
                setattr(server, 'node_processes', node_group.node_processes)
                servers.append(server)

        return servers

    def _parse_services(self, template_json):
        for s in template_json['services']:
            service = Service(s['name'])

            self.services.append(service)
            for c in s['components']:
                component = Component(c['name'], c['type'], c['cardinality'])
                service.add_component(component)

            if 'users' in s:
                for u in s['users']:
                    user = User(u['name'], u['password'], u['groups'])
                    service.add_user(user)

            configs = self._parse_configurations(s)
            for config in configs:
                service.add_configuration(config)

    def _parse_configurations(self, template_json):
        config_names = []
        for config in template_json['configurations']:
            config_props = {}
            name = config['name']
            config_names.append(name)
            if name in self.configurations:
                config_props = self.configurations[name]
            else:
                self.configurations[name] = config_props

            if 'properties' in config:
                for prop in config['properties']:
                    config_props[prop['name']] = prop['value']

        return config_names

    def _parse_host_component_mappings(self, template_json):
        for group in template_json['host_role_mappings']:
            node_group = NodeGroup(group['name'].lower())
            for component in group['components']:
                node_group.add_component(component['name'])
            for host in group['hosts']:
                if 'predicate' in host:
                    node_group.predicate = host['predicate']
                if 'cardinality' in host:
                    node_group.cardinality = host['cardinality']
                if 'default_count' in host:
                    node_group.default_count = host['default_count']
            self.node_groups[node_group.name] = node_group

    def _replace_config_tokens(self, cluster_template):
        ambari_server = self.determine_host_for_server_component(
            'AMBARI_SERVER')
        nn_server = self.determine_host_for_server_component(
            'NAMENODE')
        snn_server = self.determine_host_for_server_component(
            'SECONDARY_NAMENODE')
        jt_server = self.determine_host_for_server_component(
            'JOBTRACKER')

        LOG.info('Replacing the following configuration tokens:')

        LOG.info('%AMBARI_HOST% : {0}'.format(ambari_server.fqdn))
        cluster_template = cluster_template.replace(
            '%AMBARI_HOST%', ambari_server.fqdn)
        if nn_server:
            LOG.info('%NN_HOST% : {0}'.format(nn_server.fqdn))
            cluster_template = cluster_template.replace(
                '%NN_HOST%', nn_server.fqdn)
        if snn_server:
            LOG.info('%SNN_HOST% : {0}'.format(snn_server.fqdn))
            cluster_template = cluster_template.replace(
                '%SNN_HOST%', snn_server.fqdn)
        if jt_server:
            LOG.info('%JT_HOST% : {0}'.format(jt_server.fqdn))
            cluster_template = cluster_template.replace(
                '%JT_HOST%', jt_server.fqdn)

        return cluster_template

    def _generate_host_manifest(self):
        host_manifest = {}
        hosts = []
        host_id = 1

        for server in self.servers:
            hosts.append({'host_id': host_id,
                          'hostname': server.hostname,
                          'role': server.role,
                          'vm_image': server.nova_info.image,
                          'vm_flavor': server.nova_info.flavor,
                          'public_ip': server.management_ip,
                          'private_ip': server.internal_ip})
            host_id += 1

        host_manifest['hosts'] = hosts
        return json.dumps(host_manifest).strip('{}')

    def _add_manifest_to_config(self, cluster_template, host_manifest):
        # add the host manifest to the enf of the cluster template

        return '{0},\n{1}\n}}'.format(cluster_template.rstrip('}'),
                                      host_manifest)


class Service():
    def __init__(self, name):
        self.name = name
        self.configurations = []
        self.components = []
        self.users = []

    def add_component(self, component):
        self.components.append(component)

    def add_configuration(self, configuration):
        self.configurations.append(configuration)

    def add_user(self, user):
        self.users.append(user)


class Component():
    def __init__(self, name, component_type, cardinality):
        self.name = name
        self.type = component_type
        self.cardinality = cardinality


class NodeGroup():
    def __init__(self, name):
        self.name = name
        self.components = []
        self.predicate = None
        self.cardinality = None
        self.default_count = None

    def add_component(self, component):
        self.components.append(component)


class User():
    def __init__(self, name, password, groups):
        self.name = name
        self.password = password
        self.groups = groups


class NormalizedClusterConfig():
    def __init__(self, cluster_spec):
        #TODO(jspeidel): get from stack config
        self.hadoop_version = '1.3.0'
        self.cluster_configs = []
        self.node_groups = []
        self.config = cfg.ConfigurationProvider(
            json.load(open(os.path.join(os.path.dirname(__file__), 'resources',
                                        'ambari-config-resource.json'), "r")))

        self._parse_configurations(cluster_spec.configurations)
        self._parse_node_groups(cluster_spec.node_groups)

    def _parse_configurations(self, configurations):
        for config_name, properties in configurations.items():
            for prop, value in properties.items():
                target = self._get_property_target(config_name, prop)
                prop_type = self._get_property_type(prop, value)
                #todo: should we supply a scope?
                self.cluster_configs.append(
                    NormalizedConfigEntry(NormalizedConfig(
                        prop, prop_type, value, target, 'cluster'), value))

    def _parse_node_groups(self, node_groups):
        for node_group in node_groups.values():
            self.node_groups.append(NormalizedNodeGroup(node_group))

    def _get_property_target(self, config, prop):
        # Once config resource is complete we won't need to fall through
        # based on config type
        target = self.config.get_applicable_target(prop)
        if not target:
            if config == 'hdfs-site':
                target = 'HDFS'
            elif config == 'mapred-site':
                target = 'MAPREDUCE'
            else:
                target = 'general'

        return target

    def _get_property_type(self, prop, value):
        #TODO(jspeidel): seems that all numeric prop values in default config
        # are encoded as strings.  This may be incorrect.
        #TODO(jspeidel): should probably analyze string value to determine if
        # it is numeric
        #TODO(jspeidel): would then need to know whether Ambari expects a
        # string or a numeric value
        prop_type = type(value).__name__
        #print 'Type: {0}'.format(prop_type)
        if prop_type == 'str' or prop_type == 'unicode' or value == '':
            return 'string'
        elif prop_type == 'int':
            return 'integer'
        elif prop_type == 'bool':
            return 'boolean'
        else:
            raise ValueError(
                "Could not determine property type for property '{0}' with "
                "value: {1}".
                format(prop, value))


class NormalizedConfig():
    def __init__(self, name, config_type, default_value, target, scope):
        self.name = name
        self.description = None
        self.type = config_type
        self.default_value = default_value
        self.is_optional = False
        self.applicable_target = target
        self.scope = scope


class NormalizedConfigEntry():
    def __init__(self, config, value):
        self.config = config
        self.value = value


class NormalizedNodeGroup():
    def __init__(self, node_group):
        self.name = node_group.name
        self.node_processes = node_group.components
        self.node_configs = None
        #TODO(jpseidel): should not have to specify img/flavor
        self.img = None
        # TODO(jmaron) the flavor will be set via an ambari blueprint setting,
        # but that setting doesn't exist yet.  It will be addressed by a bug
        # fix shortly
        self.flavor = 3
        self.count = node_group.default_count
        #TODO(jspeidel): self.requirements
