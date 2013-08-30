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

import copy

from savanna.db import base as db_base
from savanna.utils import configs
# from savanna.openstack.common.rpc import common as rpc_common


CLUSTER_DEFAULTS = {
    "cluster_configs": {},
    "anti_affinity": [],
    "status": "undefined",
    "status_description": "",
    "info": {},
}

NODE_GROUP_DEFAULTS = {
    "node_processes": [],
    "node_configs": {},
    "volumes_per_node": 0,
    "volumes_size": 0,
    "volume_mount_prefix": "",
}

INSTANCE_DEFAULTS = {
    "volumes": []
}

DATA_SOURCE_DEFAULTS = {
    "credentials": {}
}


def _apply_defaults(values, defaults):
    new_values = copy.deepcopy(defaults)
    new_values.update(values)
    return new_values


class ConductorManager(db_base.Base):
    """This class aimed to conduct things.

    The methods in the base API for savanna-conductor are various proxy
    operations that allows other services to get specific work done without
    locally accessing the database.

    Additionally it performs some template-to-object copying magic.
    """

    def __init__(self):
        super(ConductorManager, self).__init__()

    ## Common helpers

    def _populate_node_groups(self, context, cluster):
        node_groups = cluster.get('node_groups')
        if not node_groups:
            return

        for node_group in node_groups:
            self._populate_node_group(context, node_group)

    def _cleanup_node_group(self, node_group):
        node_group.pop('id', None)
        node_group.pop('created_at', None)
        node_group.pop('updated_at', None)

    def _populate_node_group(self, context, node_group):
        ng_tmpl_id = node_group.get('node_group_template_id')
        if not ng_tmpl_id:
            node_group.update(_apply_defaults(node_group, NODE_GROUP_DEFAULTS))
            self._cleanup_node_group(node_group)
            return

        ng_tmpl = self.node_group_template_get(context, ng_tmpl_id)
        if not ng_tmpl:
            node_group.update(_apply_defaults(node_group, NODE_GROUP_DEFAULTS))
            self._cleanup_node_group(node_group)
            return

        new_values = _apply_defaults(ng_tmpl, NODE_GROUP_DEFAULTS)
        new_values.update(node_group)
        new_values['node_configs'] = configs.merge_configs(
            ng_tmpl.get('node_configs'),
            node_group.get('node_configs'))

        node_group.clear()
        node_group.update(new_values)

        self._cleanup_node_group(node_group)

    ## Cluster ops

    def cluster_get(self, context, cluster):
        """Return the cluster or None if it does not exist."""
        return self.db.cluster_get(context, cluster)

    def cluster_get_all(self, context):
        """Get all clusters."""
        return self.db.cluster_get_all(context)

    def cluster_create(self, context, values):
        """Create a cluster from the values dictionary."""
        values = copy.deepcopy(values)
        values = _apply_defaults(values, CLUSTER_DEFAULTS)
        values['tenant_id'] = context.tenant_id

        cluster_template_id = values.get('cluster_template_id')
        if cluster_template_id:
            c_tmpl = self.cluster_template_get(context, cluster_template_id)
            if c_tmpl:
                new_values = c_tmpl.copy()
                del new_values['created_at']
                del new_values['updated_at']
                del new_values['id']
                new_values.update(values)
                new_values['cluster_configs'] = configs.merge_configs(
                    c_tmpl.get('cluster_configs'),
                    values.get('cluster_configs'))

                values = new_values

        self._populate_node_groups(context, values)
        return self.db.cluster_create(context, values)

    def cluster_update(self, context, cluster, values):
        """Set the given properties on cluster and update it."""
        values = copy.deepcopy(values)
        return self.db.cluster_update(context, cluster, values)

    def cluster_destroy(self, context, cluster):
        """Destroy the cluster or raise if it does not exist."""
        self.db.cluster_destroy(context, cluster)

    ## Node Group ops

    def node_group_add(self, context, cluster, values):
        """Create a Node Group from the values dictionary."""
        values = copy.deepcopy(values)
        self._populate_node_group(context, values)
        return self.db.node_group_add(context, cluster, values)

    def node_group_update(self, context, node_group, values):
        """Set the given properties on node_group and update it."""
        values = copy.deepcopy(values)
        self.db.node_group_update(context, node_group, values)

    def node_group_remove(self, context, node_group):
        """Destroy the node_group or raise if it does not exist."""
        self.db.node_group_remove(context, node_group)

    ## Instance ops

    def instance_add(self, context, node_group, values):
        """Create an Instance from the values dictionary."""
        values = copy.deepcopy(values)
        values = _apply_defaults(values, INSTANCE_DEFAULTS)
        return self.db.instance_add(context, node_group, values)

    def instance_update(self, context, instance, values):
        """Set the given properties on Instance and update it."""
        values = copy.deepcopy(values)
        self.db.instance_update(context, instance, values)

    def instance_remove(self, context, instance):
        """Destroy the Instance or raise if it does not exist."""
        self.db.instance_remove(context, instance)

    ## Volumes ops

    def append_volume(self, context, instance, volume_id):
        """Append volume_id to instance."""
        self.db.append_volume(context, instance, volume_id)

    def remove_volume(self, context, instance, volume_id):
        """Remove volume_id in instance."""
        self.db.remove_volume(context, instance, volume_id)

    ## Cluster Template ops

    def cluster_template_get(self, context, cluster_template):
        """Return the cluster_template or None if it does not exist."""
        return self.db.cluster_template_get(context, cluster_template)

    def cluster_template_get_all(self, context):
        """Get all cluster_templates."""
        return self.db.cluster_template_get_all(context)

    def cluster_template_create(self, context, values):
        """Create a cluster_template from the values dictionary."""
        values = copy.deepcopy(values)
        values = _apply_defaults(values, CLUSTER_DEFAULTS)
        values['tenant_id'] = context.tenant_id

        self._populate_node_groups(context, values)

        return self.db.cluster_template_create(context, values)

    def cluster_template_destroy(self, context, cluster_template):
        """Destroy the cluster_template or raise if it does not exist."""
        self.db.cluster_template_destroy(context, cluster_template)

    ## Node Group Template ops

    def node_group_template_get(self, context, node_group_template):
        """Return the Node Group Template or None if it does not exist."""
        return self.db.node_group_template_get(context, node_group_template)

    def node_group_template_get_all(self, context):
        """Get all Node Group Templates."""
        return self.db.node_group_template_get_all(context)

    def node_group_template_create(self, context, values):
        """Create a Node Group Template from the values dictionary."""
        values = copy.deepcopy(values)
        values = _apply_defaults(values, NODE_GROUP_DEFAULTS)
        values['tenant_id'] = context.tenant_id

        return self.db.node_group_template_create(context, values)

    def node_group_template_destroy(self, context, node_group_template):
        """Destroy the Node Group Template or raise if it does not exist."""
        self.db.node_group_template_destroy(context, node_group_template)

    ## Data Source ops

    def data_source_get(self, context, data_source):
        """Return the Data Source or None if it does not exist."""
        return self.db.data_source_get(context, data_source)

    def data_source_get_all(self, context):
        """Get all Data Sources."""
        return self.db.data_source_get_all(context)

    def data_source_create(self, context, values):
        """Create a Data Source from the values dictionary."""
        values = copy.deepcopy(values)
        values = _apply_defaults(values, DATA_SOURCE_DEFAULTS)
        values['tenant_id'] = context.tenant_id

        return self.db.data_source_create(context, values)

    def data_source_destroy(self, context, data_source):
        """Destroy the Data Source or raise if it does not exist."""
        return self.db.data_source_destroy(context, data_source)

    ##Job ops

    def job_get(self, context, job):
        """Return the Job or None if it does not exist."""
        return self.db.job_get(context, job)

    def job_get_all(self, context):
        """Get all Jobs."""
        return self.db.job_get_all(context)

    def job_create(self, context, values):
        """Create a Job from the values dictionary."""
        values = copy.deepcopy(values)
        values['tenant_id'] = context.tenant_id
        return self.db.job_create(context, values)

    def job_destroy(self, context, job):
        """Destroy the Job or raise if it does not exist."""
        return self.db.job_destroy(context, job)

    ##JobExecution ops

    def job_execution_get(self, context, job_execution):
        """Return the JobExecution or None if it does not exist."""
        return self.db.job_execution_get(context, job_execution)

    def job_execution_get_all(self, context):
        """Get all JobExecutions."""
        return self.db.job_execution_get_all(context)

    def job_execution_create(self, context, values):
        """Create a JobExecution from the values dictionary."""
        values['tenant_id'] = context.tenant_id
        return self.db.job_execution_create(context, values)

    def job_execution_update(self, context, job_execution, values):
        """Updates a JobExecution from the values dictionary."""
        return self.db.job_execution_update(context, job_execution, values)

    def job_execution_destroy(self, context, job_execution):
        """Destroy the JobExecution or raise if it does not exist."""
        return self.db.job_execution_destroy(context, job_execution)

    ## JobOrigin ops

    def job_origin_get(self, context, job_origin):
        """Return the JobOrigin or None if it does not exist."""
        return self.db.job_origin_get(context, job_origin)

    def job_origin_get_all(self, context):
        """Get all JobOrigins."""
        return self.db.job_origin_get_all(context)

    def job_origin_create(self, context, values):
        """Create a JobOrigin from the values dictionary."""
        values = copy.deepcopy(values)
        values['tenant_id'] = context.tenant_id
        return self.db.job_origin_create(context, values)

    def job_origin_update(self, context, job_origin, values):
        """Updates a JobOrigin from the values dictionary."""
        return self.db.job_origin_update(context, job_origin, values)

    def job_origin_destroy(self, context, job_origin):
        """Destroy the JobOrigin or raise if it does not exist."""
        self.db.job_origin_destroy(context, job_origin)

    ## JobBinary ops

    def job_binary_get_all(self, context):
        """Get all JobBinarys

        The JobBinarys returned do not contain a data field.
        """
        return self.db.job_binary_get_all(context)

    def job_binary_get(self, context, job_binary_id):
        """Return the JobBinary or None if it does not exist

        The JobBinary returned does not contain a data field.
        """
        return self.db.job_binary_get(context, job_binary_id)

    def job_binary_create(self, context, values):
        """Create a JobBinary from the values dictionary."""

        # Since values["data"] is (should be) encoded as a string
        # here the deepcopy of values only incs a reference count on data.
        # This is nice, since data could be big...
        values = copy.deepcopy(values)
        values['tenant_id'] = context.tenant_id
        values['datasize'] = len(values["data"])
        return self.db.job_binary_create(context, values)

    def job_binary_destroy(self, context, job_binary):
        """Destroy the JobBinary or raise if it does not exist."""
        self.db.job_binary_destroy(context, job_binary)

    def job_binary_get_raw_data(self, context, job_binary_id):
        """Return the binary data field from the specified JobBinary."""
        return self.db.job_binary_get_raw_data(context, job_binary_id)
