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

from oslo_log import log as logging
from oslo_serialization import jsonutils as json

from sahara.i18n import _
from sahara.plugins import exceptions as ex
from sahara.plugins.hdp.versions import versionhandlerfactory as vhf


LOG = logging.getLogger(__name__)


def validate_number_of_datanodes(cluster, scaled_groups, default_configs):
    dfs_replication = 0
    for config in default_configs:
        if config.name == 'dfs.replication':
            dfs_replication = config.default_value
    conf = cluster.cluster_configs
    if 'HDFS' in conf and 'dfs.replication' in conf['HDFS']:
        dfs_replication = conf['HDFS']['dfs.replication']

    if not scaled_groups:
        scaled_groups = {}
    dn_count = 0
    for ng in cluster.node_groups:
        if 'DATANODE' in ng.node_processes:
            if ng.id in scaled_groups:
                dn_count += scaled_groups[ng.id]
            else:
                dn_count += ng.count

    if dn_count < int(dfs_replication):
        raise ex.InvalidComponentCountException(
            'datanode', _('%s or more') % dfs_replication, dn_count,
            _('Number of %(dn)s instances should not be less '
              'than %(replication)s')
            % {'dn': 'DATANODE', 'replication': 'dfs.replication'})


class ClusterSpec(object):
    def __init__(self, config, version='1.3.2'):
        self._config_template = config
        self.services = []
        self.configurations = {}
        self.node_groups = {}
        self.version = version
        self.user_input_handlers = {}

        cluster_template = json.loads(config)
        self._parse_services(cluster_template)
        self._parse_configurations(cluster_template)
        self._process_node_groups(template_json=cluster_template)

    def create_operational_config(self, cluster, user_inputs,
                                  scaled_groups=None):
        if scaled_groups is None:
            scaled_groups = {}
        self._determine_deployed_services(cluster)
        self._process_node_groups(cluster=cluster)

        for ng_id in scaled_groups:
            existing = next(group for group in self.node_groups.values()
                            if group.id == ng_id)
            existing.count = scaled_groups[ng_id]

        self.validate_node_groups(cluster)
        self._finalize_ng_components()
        self._parse_configurations(json.loads(self._config_template))
        self._process_user_inputs(user_inputs)
        self._replace_config_tokens()

    def scale(self, updated_groups):
        for ng_id in updated_groups:
            existing = next(group for group in self.node_groups.values()
                            if group.id == ng_id)
            existing.count = updated_groups[ng_id]

    def validate_node_groups(self, cluster):
        for service in self.services:
            if service.deployed:
                service.validate(self, cluster)
            elif service.is_mandatory():
                raise ex.RequiredServiceMissingException(service.name)

    def get_deployed_configurations(self):
        configs = set()
        for service in self.services:
            if service.deployed:
                configs |= service.configurations

        return configs

    def determine_component_hosts(self, component):
        hosts = set()
        for ng in self.node_groups.values():
            if component in ng.components:
                hosts |= ng.instances

        return hosts

    def normalize(self):
        return NormalizedClusterConfig(self)

    def get_deployed_node_group_count(self, name):
        count = 0
        for ng in self.get_node_groups_containing_component(name):
            count += ng.count

        return count

    def get_node_groups_containing_component(self, component):
        found_node_groups = []
        for ng in self.node_groups.values():
            if component in ng.components:
                found_node_groups.append(ng)

        return found_node_groups

    def get_components_for_type(self, type):
        components = set()
        for service in self.services:
            for component in service.components:
                if component.type == type:
                    components.add(component.name)

        return components

    def is_hdfs_ha_enabled(self, cluster):
        if self.version == '2.0.6':
            if cluster.cluster_configs.get('HDFSHA', False):
                if cluster.cluster_configs.HDFSHA.get('hdfs.nnha',
                                                      False) is True:
                    return True
        return False

    def _parse_services(self, template_json):
        handler = (vhf.VersionHandlerFactory.get_instance().
                   get_version_handler(self.version))
        sp = handler.get_services_processor()
        for s in template_json['services']:
            name = s['name']
            service = sp.create_service(name)

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

    def _process_node_groups(self, template_json=None, cluster=None):
        # get node_groups from config
        if template_json and not cluster:
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
                        node_group.count = host['default_count']
                self.node_groups[node_group.name] = node_group

        if cluster:
            self.node_groups = {}
            node_groups = cluster.node_groups
            for ng in node_groups:
                node_group = NodeGroup(ng.name.lower())
                node_group.count = ng.count
                node_group.id = ng.id
                node_group.components = ng.node_processes[:]
                node_group.ng_storage_paths = ng.storage_paths()
                for instance in ng.instances:
                    node_group.instances.add(Instance(instance))
                self.node_groups[node_group.name] = node_group

    def _determine_deployed_services(self, cluster):
        for ng in cluster.node_groups:
            for service in self.services:
                if service.deployed:
                    continue
                for sc in service.components:
                    if sc.name in ng.node_processes:
                        service.deployed = True
                        service.register_user_input_handlers(
                            self.user_input_handlers)
                        break

    def _process_user_inputs(self, user_inputs):
        for ui in user_inputs:
            user_input_handler = self.user_input_handlers.get(
                '{0}/{1}'.format(ui.config.tag, ui.config.name),
                self._default_user_input_handler)

            user_input_handler(ui, self.configurations)

    def _replace_config_tokens(self):
        for service in self.services:
            if service.deployed:
                service.finalize_configuration(self)

    def _finalize_ng_components(self):
        for service in self.services:
            if service.deployed:
                service.finalize_ng_components(self)

    def _default_user_input_handler(self, user_input, configurations):
        config_map = configurations[user_input.config.tag]
        config_map[user_input.config.name] = user_input.value


class Component(object):
    def __init__(self, name, component_type, cardinality):
        self.name = name
        self.type = component_type
        self.cardinality = cardinality


class NodeGroup(object):
    def __init__(self, name):
        self.id = None
        self.name = name
        self.components = []
        self.predicate = None
        self.cardinality = None
        self.count = None
        self.instances = set()
        self.ng_storage_paths = []

    def add_component(self, component):
        self.components.append(component)

    def storage_paths(self):
        return self.ng_storage_paths


class User(object):
    def __init__(self, name, password, groups):
        self.name = name
        self.password = password
        self.groups = groups


class Instance(object):
    def __init__(self, sahara_instance):
        self.inst_fqdn = sahara_instance.fqdn()
        self.management_ip = sahara_instance.management_ip
        self.internal_ip = sahara_instance.internal_ip
        self.sahara_instance = sahara_instance

    def fqdn(self):
        return self.inst_fqdn

    def remote(self):
        return self.sahara_instance.remote()

    def __hash__(self):
        return hash(self.fqdn())

    def __eq__(self, other):
        return self.fqdn() == other.fqdn()


class NormalizedClusterConfig(object):
    def __init__(self, cluster_spec):
        self.hadoop_version = cluster_spec.version
        self.cluster_configs = []
        self.node_groups = []
        self.handler = (vhf.VersionHandlerFactory.get_instance().
                        get_version_handler(self.hadoop_version))

        self._parse_configurations(cluster_spec.configurations)
        self._parse_node_groups(cluster_spec.node_groups)

    def _parse_configurations(self, configurations):
        for config_name, properties in configurations.items():
            for prop, value in properties.items():
                target = self._get_property_target(prop)
                if target:
                    prop_type = self._get_property_type(prop, value)
                    # TODO(sdpeidel): should we supply a scope?
                    self.cluster_configs.append(
                        NormalizedConfigEntry(NormalizedConfig(
                            prop, prop_type, value, target, 'cluster'),
                            value))

    def _parse_node_groups(self, node_groups):
        for node_group in node_groups.values():
            self.node_groups.append(NormalizedNodeGroup(node_group))

    def _get_property_target(self, prop):
        return self.handler.get_applicable_target(prop)

    def _get_property_type(self, prop, value):
        # TODO(jspeidel): seems that all numeric prop values in default config
        # are encoded as strings.  This may be incorrect.
        # TODO(jspeidel): should probably analyze string value to determine if
        # it is numeric
        # TODO(jspeidel): would then need to know whether Ambari expects a
        # string or a numeric value
        prop_type = type(value).__name__
        # print 'Type: {0}'.format(prop_type)
        if prop_type == 'str' or prop_type == 'unicode' or value == '':
            return 'string'
        elif prop_type == 'int':
            return 'integer'
        elif prop_type == 'bool':
            return 'boolean'
        else:
            raise ValueError(
                _("Could not determine property type for property "
                  "'%(property)s' with value: %(value)s") %
                {"property": prop, "value": value})


class NormalizedConfig(object):
    def __init__(self, name, config_type, default_value, target, scope):
        self.name = name
        self.description = None
        self.type = config_type
        self.default_value = default_value
        self.is_optional = False
        self.applicable_target = target
        self.scope = scope


class NormalizedConfigEntry(object):
    def __init__(self, config, value):
        self.config = config
        self.value = value


class NormalizedNodeGroup(object):
    def __init__(self, node_group):
        self.name = node_group.name
        self.node_processes = node_group.components
        self.node_configs = None
        # TODO(jpseidel): should not have to specify img/flavor
        self.img = None
        # TODO(jmaron) the flavor will be set via an ambari blueprint setting,
        # but that setting doesn't exist yet.  It will be addressed by a bug
        # fix shortly
        self.flavor = 3
        self.count = node_group.count
        self.id = node_group.id
