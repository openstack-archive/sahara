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

"""Handles database requests from other savanna services."""

# from savanna.openstack.common.rpc import common as rpc_common
from savanna.db_new import base as db_base


class ConductorManager(db_base.Base):
    """This class aimed to conduct things.

    The methods in the base API for savanna-conductor are various proxy
    operations that allows other services to get specific work done without
    locally accessing the database.
    """

    def __init__(self):
        super(ConductorManager, self).__init__()

    ## Cluster ops

    # @resource(Cluster)
    def cluster_get(self, context, cluster):
        """Return the cluster or None if it does not exist."""
        return self.db.cluster_get(context, cluster)

    def cluster_get_all(self, context):
        """Get all clusters."""
        return self.db.cluster_get_all(context)

    def cluster_create(self, context, values):
        """Create a cluster from the values dictionary."""
        return self.db.cluster_create(context, values)

    def cluster_update(self, context, cluster, values):
        """Set the given properties on cluster and update it."""
        return self.db.cluster_update(context, cluster, values)

    def cluster_destroy(self, context, cluster):
        """Destroy the cluster or raise if it does not exist."""
        self.db.cluster_destroy(context, cluster)

    ## Node Group ops

    def node_group_add(self, context, cluster, values):
        """Create a Node Group from the values dictionary."""
        return self.db.node_group_add(context, cluster, values)

    def node_group_update(self, context, node_group, values):
        """Set the given properties on node_group and update it."""
        return self.db.node_group_update(context, node_group, values)

    def node_group_remove(self, context, node_group):
        """Destroy the node_group or raise if it does not exist."""
        self.db.node_group_remove(context, node_group)

    ## Instance ops

    # @resource(Instance)
    def instance_add(self, context, node_group, values):
        """Create an Instance from the values dictionary."""
        return self.db.instance_add(context, node_group, values)

    def instance_update(self, context, instance, values):
        """Set the given properties on Instance and update it."""
        return self.db.instance_update(context, instance, values)

    def instance_remove(self, context, instance):
        """Destroy the Instance or raise if it does not exist."""
        self.db.instance_remove(context, instance)

    ## Cluster Template ops

    # @resource(ClusterTemplate)
    def cluster_template_get(self, context, cluster_template):
        """Return the cluster_template or None if it does not exist."""
        return self.db.cluster_template_get(context, cluster_template)

    def cluster_template_get_all(self, context):
        """Get all cluster_templates."""
        return self.db.cluster_template_get_all(context)

    def cluster_template_create(self, context, values):
        """Create a cluster_template from the values dictionary."""
        return self.db.cluster_template_create(context, values)

    def cluster_template_destroy(self, context, cluster_template):
        """Destroy the cluster_template or raise if it does not exist."""
        self.db.cluster_template_destroy(context, cluster_template)

    ## Node Group Template ops

    # @resource(NodeGroupTemplate)
    def node_group_template_get(self, context, node_group_template):
        """Return the Node Group Template or None if it does not exist."""
        return self.db.node_group_template_get(context, node_group_template)

    def node_group_template_get_all(self, context):
        """Get all Node Group Templates."""
        return self.db.node_group_template_get_all(context)

    def node_group_template_create(self, context, values):
        """Create a Node Group Template from the values dictionary."""
        return self.db.node_group_template_create(context, values)

    def node_group_template_destroy(self, context, node_group_template):
        """Destroy the Node Group Template or raise if it does not exist."""
        self.db.node_group_template_destroy(context, node_group_template)
