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


from sahara import context
import sahara.exceptions as ex
from sahara.i18n import _
import sahara.plugins.base as plugin_base
from sahara.service import api as service_api
from sahara.service.api import v10 as api
from sahara.service.validations import acl
import sahara.service.validations.base as b
from sahara.utils import cluster as c_u


def check_cluster_scaling(data, cluster_id, **kwargs):
    ctx = context.current()
    cluster = api.get_cluster(id=cluster_id)

    if cluster is None:
        raise ex.NotFoundException(
            {'id': cluster_id}, _('Object with %s not found'))

    b.check_plugin_labels(
        cluster.plugin_name, cluster.hadoop_version)

    acl.check_tenant_for_update(ctx, cluster)
    acl.check_protected_from_update(cluster, data)

    cluster_engine = cluster.sahara_info.get(
        'infrastructure_engine') if cluster.sahara_info else None

    engine_type_and_version = service_api.OPS.get_engine_type_and_version()
    if (not cluster_engine and
            not engine_type_and_version.startswith('direct')):
        raise ex.InvalidReferenceException(
            _("Cluster created before Juno release "
              "can't be scaled with %(engine)s engine") %
            {"engine": engine_type_and_version})

    if (cluster.sahara_info and
            cluster_engine != engine_type_and_version):
        raise ex.InvalidReferenceException(
            _("Cluster created with %(old_engine)s infrastructure engine "
              "can't be scaled with %(new_engine)s engine") %
            {"old_engine": cluster.sahara_info.get('infrastructure_engine'),
             "new_engine": engine_type_and_version})

    if not (plugin_base.PLUGINS.is_plugin_implements(cluster.plugin_name,
                                                     'scale_cluster') and (
            plugin_base.PLUGINS.is_plugin_implements(cluster.plugin_name,
                                                     'decommission_nodes'))):
        raise ex.InvalidReferenceException(
            _("Requested plugin '%s' doesn't support cluster scaling feature")
            % cluster.plugin_name)

    if cluster.status != c_u.CLUSTER_STATUS_ACTIVE:
        raise ex.InvalidReferenceException(
            _("Cluster cannot be scaled not in 'Active' status. "
              "Cluster status: %s") % cluster.status)

    if cluster.user_keypair_id:
        b.check_keypair_exists(cluster.user_keypair_id)

    if cluster.default_image_id:
        b.check_image_registered(cluster.default_image_id)

    if data.get("resize_node_groups"):
        b.check_resize(cluster, data['resize_node_groups'])

    if data.get("add_node_groups"):
        b.check_add_node_groups(cluster, data['add_node_groups'])
        b.check_cluster_hostnames_lengths(cluster.name,
                                          data['add_node_groups'])
