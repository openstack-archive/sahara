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

from oslo_config import cfg

from sahara import context
import sahara.exceptions as ex
from sahara.i18n import _
from sahara.service.api import v10 as api
from sahara.service.health import verification_base
from sahara.service.validations import acl
import sahara.service.validations.base as b

CONF = cfg.CONF


def check_cluster_create(data, **kwargs):
    b.check_cluster_unique_name(data['name'])
    _check_cluster_create(data)


def check_multiple_clusters_create(data, **kwargs):
    _check_cluster_create(data)
    for counter in range(data['count']):
        cluster_name = api.get_multiple_cluster_name(data['count'],
                                                     data['name'],
                                                     counter + 1)
        b.check_cluster_unique_name(cluster_name)


def check_one_or_multiple_clusters_create(data, **kwargs):
    if data.get('count', None) is not None:
        check_multiple_clusters_create(data, **kwargs)
    else:
        check_cluster_create(data, **kwargs)


def _check_cluster_create(data):
    plugin_version = 'hadoop_version'
    if data.get('plugin_version'):
        plugin_version = 'plugin_version'
    b.check_plugin_name_exists(data['plugin_name'])
    b.check_plugin_supports_version(data['plugin_name'],
                                    data[plugin_version])
    b.check_plugin_labels(
        data['plugin_name'], data[plugin_version])

    if data.get('cluster_template_id'):
        ct_id = data['cluster_template_id']
        b.check_cluster_template_exists(ct_id)
        if not data.get('node_groups'):
            b.check_node_groups_in_cluster_templates(data['name'],
                                                     data['plugin_name'],
                                                     data[plugin_version],
                                                     ct_id)

    if data.get('user_keypair_id'):
        b.check_keypair_exists(data['user_keypair_id'])

    default_image_id = _get_cluster_field(data, 'default_image_id')
    if default_image_id:
        b.check_image_registered(default_image_id)
        b.check_required_image_tags(data['plugin_name'],
                                    data[plugin_version],
                                    default_image_id)
    else:
        raise ex.NotFoundException('default_image_id',
                                   _("'%s' field is not found"))

    b.check_all_configurations(data)

    if data.get('anti_affinity'):
        b.check_node_processes(data['plugin_name'], data[plugin_version],
                               data['anti_affinity'])

    if data.get('node_groups'):
        b.check_cluster_hostnames_lengths(data['name'], data['node_groups'])

    neutron_net_id = _get_cluster_field(data, 'neutron_management_network')
    if neutron_net_id:
        b.check_network_exists(neutron_net_id)
    else:
        raise ex.NotFoundException('neutron_management_network',
                                   _("'%s' field is not found"))


def _get_cluster_field(cluster, field):
    if cluster.get(field):
        return cluster[field]

    if cluster.get('cluster_template_id'):
        cluster_template = api.get_cluster_template(
            id=cluster['cluster_template_id'])

        if cluster_template.get(field):
            return cluster_template[field]

    return None


def check_cluster_delete(cluster_id, **kwargs):
    cluster = api.get_cluster(cluster_id)

    acl.check_tenant_for_delete(context.current(), cluster)
    acl.check_protected_from_delete(cluster)


def check_cluster_update(cluster_id, data, **kwargs):
    cluster = api.get_cluster(cluster_id)

    verification = verification_base.validate_verification_ops(
        cluster, data)
    acl.check_tenant_for_update(context.current(), cluster)
    if not verification:
        acl.check_protected_from_update(cluster, data)
