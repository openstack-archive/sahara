# Copyright (c) 2013 Mirantis Inc.
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

import collections

import novaclient.exceptions as nova_ex
from oslo_config import cfg
from oslo_utils import uuidutils
import six

from sahara import conductor as cond
from sahara import context
import sahara.exceptions as ex
from sahara.i18n import _
import sahara.plugins.base as plugin_base
from sahara.service.api import v10 as api
from sahara.utils import general as g
import sahara.utils.openstack.cinder as cinder
from sahara.utils.openstack import images as sahara_images
import sahara.utils.openstack.neutron as neutron
import sahara.utils.openstack.nova as nova


CONF = cfg.CONF
conductor = cond.API

MAX_HOSTNAME_LENGTH = 64


def _get_plugin_configs(plugin_name, hadoop_version, scope=None):
    pl_confs = {}
    for config in plugin_base.PLUGINS.get_plugin(
            plugin_name).get_all_configs(hadoop_version):
        if pl_confs.get(config.applicable_target):
            pl_confs[config.applicable_target].append(config.name)
        else:
            pl_confs[config.applicable_target] = [config.name]
    return pl_confs


def _check_duplicates(lst, message):
    invalid = []
    lst = collections.Counter(lst)
    for key, value in six.iteritems(lst):
        if value > 1:
            invalid.append(key)

    if len(invalid) > 0:
        raise ex.InvalidDataException(message % invalid)


# Common validation checks

def check_plugin_name_exists(name):
    if name not in [p.name for p in api.get_plugins()]:
        raise ex.InvalidReferenceException(
            _("Sahara doesn't contain plugin with name '%s'") % name)


def check_plugin_supports_version(p_name, version):
    if version not in plugin_base.PLUGINS.get_plugin(p_name).get_versions():
        raise ex.InvalidReferenceException(
            _("Requested plugin '%(name)s' doesn't support version "
              "'%(version)s'") % {'name': p_name, 'version': version})


def check_plugin_labels(p_name, version):
    plugin_base.PLUGINS.validate_plugin_labels(p_name, version)


def check_image_registered(image_id):
    if image_id not in (
            [i.id for i in sahara_images.image_manager().list_registered()]):
        raise ex.InvalidReferenceException(
            _("Requested image '%s' is not registered") % image_id)


def check_node_group_configs(plugin_name, hadoop_version, ng_configs,
                             plugin_configs=None):
    # TODO(aignatov): Should have scope and config type validations
    pl_confs = plugin_configs or _get_plugin_configs(plugin_name,
                                                     hadoop_version)
    for app_target, configs in ng_configs.items():
        if app_target not in pl_confs:
            raise ex.InvalidReferenceException(
                _("Plugin doesn't contain applicable target '%s'")
                % app_target)
        for name, values in configs.items():
            if name not in pl_confs[app_target]:
                raise ex.InvalidReferenceException(
                    _("Plugin's applicable target '%(target)s' doesn't "
                      "contain config with name '%(name)s'") %
                    {'target': app_target, 'name': name})


def check_all_configurations(data):
    plugin_version = 'hadoop_version'
    if data.get('plugin_version'):
        plugin_version = 'plugin_version'

    pl_confs = _get_plugin_configs(data['plugin_name'], data[plugin_version])

    if data.get('cluster_configs'):
        check_node_group_configs(data['plugin_name'], data[plugin_version],
                                 data['cluster_configs'],
                                 plugin_configs=pl_confs)

    if data.get('node_groups'):
        check_duplicates_node_groups_names(data['node_groups'])
        for ng in data['node_groups']:
            check_node_group_basic_fields(data['plugin_name'],
                                          data[plugin_version],
                                          ng, pl_confs)

# NodeGroup related checks


def check_node_group_basic_fields(plugin_name, hadoop_version, ng,
                                  plugin_configs=None):

    if ng.get('node_group_template_id'):
        ng_tmpl_id = ng['node_group_template_id']
        check_node_group_template_exists(ng_tmpl_id)
        ng_tmpl = api.get_node_group_template(ng_tmpl_id).to_wrapped_dict()
        check_node_group_basic_fields(plugin_name, hadoop_version,
                                      ng_tmpl['node_group_template'],
                                      plugin_configs)

    if ng.get('node_configs'):
        check_node_group_configs(plugin_name, hadoop_version,
                                 ng['node_configs'], plugin_configs)
    if ng.get('flavor_id'):
        check_flavor_exists(ng['flavor_id'])

    if ng.get('node_processes'):
        check_node_processes(plugin_name, hadoop_version, ng['node_processes'])

    if ng.get('image_id'):
        check_image_registered(ng['image_id'])

    if ng.get('volumes_per_node'):
        if not cinder.check_cinder_exists():
            raise ex.InvalidReferenceException(_("Cinder is not supported"))

        if ng.get('volumes_availability_zone'):
            check_volume_availability_zone_exist(
                ng['volumes_availability_zone'])

        if ng.get('volume_type'):
            check_volume_type_exists(ng['volume_type'])

        if not ng.get('volumes_size'):
            raise ex.InvalidReferenceException(
                _("You must specify a volumes_size parameter"))

    if ng.get('floating_ip_pool'):
        check_floatingip_pool_exists(ng['floating_ip_pool'])

    if ng.get('security_groups'):
        check_security_groups_exist(ng['security_groups'])

    if ng.get('availability_zone'):
        check_availability_zone_exist(ng['availability_zone'])


def check_flavor_exists(flavor_id):
    flavor_list = nova.client().flavors.list()
    if flavor_id not in [flavor.id for flavor in flavor_list]:
        raise ex.NotFoundException(
            flavor_id, _("Requested flavor '%s' not found"))


def check_security_groups_exist(security_groups):
    security_group_list = neutron.client().list_security_groups()
    allowed_groups = set()
    for sg in security_group_list['security_groups']:
        allowed_groups.add(sg['name'])
        allowed_groups.add(sg['id'])

    for sg in security_groups:
        if sg not in allowed_groups:
            raise ex.NotFoundException(
                sg, _("Security group '%s' not found"))


def check_floatingip_pool_exists(pool_id):
    network = None
    network = neutron.get_network(pool_id)

    if not network:
        raise ex.NotFoundException(pool_id, _("Floating IP pool %s not found"))


def check_node_processes(plugin_name, version, node_processes):
    _check_duplicates(node_processes, _("Duplicates in node processes have "
                                        "been detected: %s"))

    plugin_processes = []
    for process in plugin_base.PLUGINS.get_plugin(
            plugin_name).get_node_processes(version).values():
        plugin_processes += process
    plugin_processes = set(plugin_processes)

    invalid_processes = []
    for node_process in node_processes:
        if node_process not in plugin_processes:
            invalid_processes.append(node_process)

    if len(invalid_processes) > 0:
        raise ex.InvalidReferenceException(
            _("Plugin doesn't support the following node processes: %s")
            % sorted(invalid_processes))


def check_duplicates_node_groups_names(node_groups):
    ng_names = [ng['name'] for ng in node_groups]
    _check_duplicates(
        ng_names, _("Duplicates in node group names are detected: %s"))


def check_availability_zone_exist(az):
    az_list = nova.client().availability_zones.list(False)
    az_names = [a.zoneName for a in az_list]
    if az not in az_names:
        raise ex.NotFoundException(
            az, _("Nova availability zone '%s' not found"))


def check_volume_availability_zone_exist(az):
    az_list = cinder.client().availability_zones.list()
    az_names = [a.zoneName for a in az_list]
    if az not in az_names:
        raise ex.NotFoundException(
            az, _("Cinder availability zone '%s' not found"))


def check_volume_type_exists(volume_type):
    volume_types = cinder.client().volume_types.list()
    volume_types = list(filter(lambda x: x.name == volume_type, volume_types))
    if len(volume_types) == 1 and volume_types[0].name == volume_type:
        return
    raise ex.NotFoundException(volume_type, _("Volume type '%s' not found"))


# Cluster creation related checks

def check_cluster_unique_name(cluster_name):
    if cluster_name in [cluster.name for cluster in
                        api.get_clusters(name=cluster_name)]:
        raise ex.NameAlreadyExistsException(
            _("Cluster with name '%s' already exists") % cluster_name)


def check_cluster_hostnames_lengths(cluster_name, node_groups):
    for ng in node_groups:
        longest_hostname = g.generate_instance_name(cluster_name,
                                                    ng['name'], ng['count'])
        longest_hostname += '.'
        longest_hostname += CONF.node_domain
        if len(longest_hostname) > MAX_HOSTNAME_LENGTH:
            raise ex.InvalidDataException(
                _("Composite hostname %(host)s in provisioned cluster exceeds"
                  " maximum limit %(limit)s characters") %
                {'host': longest_hostname,
                 'limit': MAX_HOSTNAME_LENGTH})


def check_keypair_exists(keypair):
    try:
        nova.client().keypairs.get(keypair)
    except nova_ex.NotFound:
        raise ex.NotFoundException(
            keypair, _("Requested keypair '%s' not found"))


def check_network_exists(net_id):
    if not neutron.get_network(net_id):
        raise ex.NotFoundException(net_id, _("Network %s not found"))


# Cluster templates related checks

def check_cluster_template_unique_name(cluster_tmpl_name):
    if cluster_tmpl_name in [cluster_tmpl.name for cluster_tmpl in
                             api.get_cluster_templates(
                                 name=cluster_tmpl_name)]:
        raise ex.NameAlreadyExistsException(
            _("Cluster template with name '%s' already exists") %
            cluster_tmpl_name)


def check_cluster_template_exists(cluster_template_id):
    if not api.get_cluster_template(id=cluster_template_id):
        raise ex.NotFoundException(
            cluster_template_id,
            _("Cluster template with id '%s' not found"))


def check_node_groups_in_cluster_templates(cluster_name, plugin_name,
                                           hadoop_version,
                                           cluster_template_id):
    c_t = api.get_cluster_template(id=cluster_template_id)
    n_groups = c_t.to_wrapped_dict()['cluster_template']['node_groups']
    for node_group in n_groups:
        check_node_group_basic_fields(plugin_name, hadoop_version, node_group)
    check_cluster_hostnames_lengths(cluster_name, n_groups)

# NodeGroup templates related checks


def check_node_group_template_unique_name(ng_tmpl_name):
    if ng_tmpl_name in [ng_tmpl.name for ng_tmpl in
                        api.get_node_group_templates(name=ng_tmpl_name)]:
        raise ex.NameAlreadyExistsException(
            _("NodeGroup template with name '%s' already exists") %
            ng_tmpl_name)


def check_node_group_template_exists(ng_tmpl_id):
    if not api.get_node_group_template(id=ng_tmpl_id):
        raise ex.NotFoundException(
            ng_tmpl_id, _("NodeGroup template with id '%s' not found"))


def _get_floating_ip_pool(node_group):
    # tmckay-fp I think this would be the method we needed to
    # get floating_ip_pool for instances
    if node_group.get('floating_ip_pool'):
        return node_group['floating_ip_pool']

    if node_group.get('node_group_template_id'):
        ctx = context.ctx()
        ngt = conductor.node_group_template_get(
            ctx,
            node_group['node_group_template_id'])
        if ngt.get('floating_ip_pool'):
            return ngt['floating_ip_pool']

    return None


# Cluster scaling

def check_resize(cluster, r_node_groups):
    ng_map = {}
    for ng in cluster.node_groups:
        ng_map[ng.name] = ng

    check_duplicates_node_groups_names(r_node_groups)

    for ng in r_node_groups:
        if ng['name'] not in ng_map.keys():
            raise ex.InvalidReferenceException(
                _("Cluster doesn't contain node group with name '%s'")
                % ng['name'])
        node_group = ng_map[ng['name']]
        if node_group.get('node_group_template_id'):
            ng_tmpl_id = node_group['node_group_template_id']
            check_node_group_template_exists(ng_tmpl_id)
            ng_tmp = api.get_node_group_template(ng_tmpl_id).to_wrapped_dict()
            check_node_group_basic_fields(cluster.plugin_name,
                                          cluster.hadoop_version,
                                          ng_tmp['node_group_template'])

    for scaling_ng in r_node_groups:
        current_count = ng_map[scaling_ng['name']].count
        new_count = scaling_ng['count']
        count_diff = current_count - new_count
        if 'instances' in scaling_ng:
            if len(scaling_ng['instances']) > count_diff:
                raise ex.InvalidDataException(
                    _("Number of specific instances (%(instance)s) to"
                      " delete can not be greater than the count difference"
                      " (%(count)s during scaling")
                    % {'instance': str(len(scaling_ng['instances'])),
                       'count': str(count_diff)})
            else:
                if len(scaling_ng['instances']) > 0:
                    is_uuid = uuidutils.is_uuid_like(
                        scaling_ng['instances'][0])
                    if is_uuid:
                        for instance in scaling_ng['instances']:
                            if not uuidutils.is_uuid_like(instance):
                                raise ex.InvalidReferenceException(
                                    _("You can only reference instances by"
                                      " Name or UUID, not both on the same"
                                      " request"))
                    else:
                        for instance in scaling_ng['instances']:
                            if uuidutils.is_uuid_like(instance):
                                raise ex.InvalidReferenceException(
                                    _("You can only reference instances by"
                                      " Name or UUID, not both on the same"
                                      " request"))
                    _check_duplicates(scaling_ng['instances'],
                                      _("Duplicate entry for instances to"
                                        " delete"))


def check_add_node_groups(cluster, add_node_groups):
    cluster_ng_names = [ng.name for ng in cluster.node_groups]

    check_duplicates_node_groups_names(add_node_groups)

    pl_confs = _get_plugin_configs(cluster.plugin_name, cluster.hadoop_version)

    for ng in add_node_groups:
        if ng['name'] in cluster_ng_names:
            raise ex.InvalidReferenceException(
                _("Can't add new nodegroup. Cluster already has nodegroup with"
                  " name '%s'") % ng['name'])

        check_node_group_basic_fields(cluster.plugin_name,
                                      cluster.hadoop_version, ng, pl_confs)


# Tags


def check_required_image_tags(plugin_name, hadoop_version, image_id):
    image = api.get_image(id=image_id)
    plugin = plugin_base.PLUGINS.get_plugin(plugin_name)
    req_tags = set(plugin.get_required_image_tags(hadoop_version))
    req_tags = list(req_tags.difference(set(image.tags)))
    if req_tags:
        raise ex.InvalidReferenceException(
            _("Requested image '%(image)s' doesn't contain required"
              " tags: %(tags)s")
            % {'image': image_id, 'tags': req_tags})
