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

"""Handles all requests to the conductor service."""

from oslo.config import cfg

from savanna.conductor import manager
from savanna.openstack.common import log as logging

conductor_opts = [
    cfg.BoolOpt('use_local',
                default=True,
                help='Perform savanna-conductor operations locally'),
]

conductor_group = cfg.OptGroup(name='conductor',
                               title='Conductor Options')

CONF = cfg.CONF
CONF.register_group(conductor_group)
CONF.register_opts(conductor_opts, conductor_group)

LOG = logging.getLogger(__name__)


def _get_id(obj):
    """Return object id.

    Allows usage of both an object or an object's ID as a parameter when
    dealing with relationships.
    """
    try:
        return obj.id
    except AttributeError:
        return obj


class LocalApi(object):
    """A local version of the conductor API that does database updates
    locally instead of via RPC.
    """

    def __init__(self):
        self._manager = manager.ConductorManager()

    ## Cluster ops

    # @resource(Cluster)
    def cluster_get(self, context, cluster):
        """Return the cluster or None if it does not exist."""
        return self._manager.cluster_get(context, _get_id(cluster))

    def cluster_get_all(self, context):
        """Get all clusters."""
        return self._manager.cluster_get_all(context)

    def cluster_create(self, context, values):
        """Create a cluster from the values dictionary."""
        return self._manager.cluster_create(context, values)

    def cluster_update(self, context, cluster, values):
        """Set the given properties on cluster and update it."""
        return self._manager.cluster_update(context, _get_id(cluster),
                                            values)

    def cluster_destroy(self, context, cluster):
        """Destroy the cluster or raise if it does not exist."""
        return self._manager.cluster_destroy(context, _get_id(cluster))

    ## Node Group ops

    def node_group_add(self, context, cluster, values):
        """Create a Node Group from the values dictionary."""
        return self._manager.node_group_add(context, _get_id(cluster),
                                            values)

    def node_group_update(self, context, node_group, values):
        """Set the given properties on node_group and update it."""
        return self._manager.node_group_update(context, _get_id(node_group),
                                               values)

    def node_group_remove(self, context, node_group):
        """Destroy the node_group or raise if it does not exist."""
        return self._manager.node_group_remove(context, _get_id(node_group))

    ## Instance ops

    # @resource(Instance)
    def instance_add(self, context, node_group, values):
        """Create an Instance from the values dictionary."""
        return self._manager.instance_add(context, _get_id(node_group), values)

    def instance_update(self, context, instance, values):
        """Set the given properties on Instance and update it."""
        return self._manager.instance_update(context, _get_id(instance),
                                             values)

    def instance_remove(self, context, instance):
        """Destroy the Instance or raise if it does not exist."""
        return self._manager.instance_remove(context, _get_id(instance))

    ## Cluster Template ops

    # @resource(ClusterTemplate)
    def cluster_template_get(self, context, cluster_template):
        """Return the cluster_template or None if it does not exist."""
        return self._manager.cluster_template_get(context,
                                                  _get_id(cluster_template))

    def cluster_template_get_all(self, context):
        """Get all cluster_templates."""
        return self._manager.cluster_template_get_all(context)

    def cluster_template_create(self, context, values):
        """Create a cluster_template from the values dictionary."""
        return self._manager.cluster_template_create(context, values)

    def cluster_template_destroy(self, context, cluster_template):
        """Destroy the cluster_template or raise if it does not exist."""
        return self._manager.cluster_template_destroy(
            context, _get_id(cluster_template))

    ## Node Group Template ops

    # @resource(NodeGroupTemplate)
    def node_group_template_get(self, context, node_group_template):
        """Return the Node Group Template or None if it does not exist."""
        return self._manager.node_group_template_get(
            context, _get_id(node_group_template))

    def node_group_template_get_all(self, context):
        """Get all Node Group Templates."""
        return self._manager.node_group_template_get_all(context)

    def node_group_template_create(self, context, values):
        """Create a Node Group Template from the values dictionary."""
        return self._manager.node_group_template_create(context, values)

    def node_group_template_destroy(self, context, node_group_template):
        """Destroy the Node Group Template or raise if it does not exist."""
        return self._manager.node_group_template_destroy(
            context, _get_id(node_group_template))


class RemoteApi(LocalApi):
    """Conductor API that does updates via RPC to the ConductorManager."""

    # TODO(slukjanov): it should override _manager and only necessary functions
