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

"""Handles database requests from other Sahara services."""

import copy

from sahara.db import base as db_base
from sahara.utils import configs
from sahara.utils import crypto


CLUSTER_DEFAULTS = {
    "cluster_configs": {},
    "status": "undefined",
    "anti_affinity": [],
    "status_description": "",
    "info": {},
    "rollback_info": {},
    "sahara_info": {},
}

NODE_GROUP_DEFAULTS = {
    "node_processes": [],
    "node_configs": {},
    "volumes_per_node": 0,
    "volumes_size": 0,
    "volumes_availability_zone": None,
    "volume_mount_prefix": "/volumes/disk",
    "volume_type": None,
    "floating_ip_pool": None,
    "security_groups": None,
    "auto_security_group": False,
    "availability_zone": None,
    "is_proxy_gateway": False,
    "volume_local_to_instance": False,
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

    The methods in the base API for sahara-conductor are various proxy
    operations that allows other services to get specific work done without
    locally accessing the database.

    Additionally it performs some template-to-object copying magic.
    """

    def __init__(self):
        super(ConductorManager, self).__init__()

    # Common helpers

    def _populate_node_groups(self, context, cluster):
        node_groups = cluster.get('node_groups')
        if not node_groups:
            return []

        populated_node_groups = []
        for node_group in node_groups:
            populated_node_group = self._populate_node_group(context,
                                                             node_group)
            self._cleanup_node_group(populated_node_group)
            populated_node_group["tenant_id"] = context.tenant_id
            populated_node_groups.append(
                populated_node_group)

        return populated_node_groups

    def _cleanup_node_group(self, node_group):
        node_group.pop('id', None)
        node_group.pop('created_at', None)
        node_group.pop('updated_at', None)

    def _populate_node_group(self, context, node_group):
        node_group_merged = copy.deepcopy(NODE_GROUP_DEFAULTS)

        ng_tmpl_id = node_group.get('node_group_template_id')
        ng_tmpl = None
        if ng_tmpl_id:
            ng_tmpl = self.node_group_template_get(context, ng_tmpl_id)

            self._cleanup_node_group(ng_tmpl)
            node_group_merged.update(ng_tmpl)

        node_group_merged.update(node_group)

        if ng_tmpl:
            node_group_merged['node_configs'] = configs.merge_configs(
                ng_tmpl.get('node_configs'),
                node_group.get('node_configs'))

        return node_group_merged

    # Cluster ops

    def cluster_get(self, context, cluster, show_progress=False):
        """Return the cluster or None if it does not exist."""
        return self.db.cluster_get(context, cluster, show_progress)

    def cluster_get_all(self, context, **kwargs):
        """Get all clusters filtered by **kwargs.

        e.g. cluster_get_all(plugin_name='vanilla', hadoop_version='1.1')
        """
        return self.db.cluster_get_all(context, **kwargs)

    def cluster_create(self, context, values):
        """Create a cluster from the values dictionary."""

        # loading defaults
        merged_values = copy.deepcopy(CLUSTER_DEFAULTS)
        merged_values['tenant_id'] = context.tenant_id

        private_key, public_key = crypto.generate_key_pair()
        merged_values['management_private_key'] = private_key
        merged_values['management_public_key'] = public_key

        cluster_template_id = values.get('cluster_template_id')
        c_tmpl = None

        if cluster_template_id:
            c_tmpl = self.cluster_template_get(context, cluster_template_id)

            del c_tmpl['created_at']
            del c_tmpl['updated_at']
            del c_tmpl['id']

            # updating with cluster_template values
            merged_values.update(c_tmpl)

        # updating with values provided in request
        merged_values.update(values)

        if c_tmpl:
            merged_values['cluster_configs'] = configs.merge_configs(
                c_tmpl.get('cluster_configs'),
                values.get('cluster_configs'))

        merged_values['node_groups'] = self._populate_node_groups(
            context, merged_values)

        return self.db.cluster_create(context, merged_values)

    def cluster_update(self, context, cluster, values):
        """Set the given properties on cluster and update it."""
        values = copy.deepcopy(values)
        return self.db.cluster_update(context, cluster, values)

    def cluster_destroy(self, context, cluster):
        """Destroy the cluster or raise if it does not exist."""
        self.db.cluster_destroy(context, cluster)

    # Node Group ops

    def node_group_add(self, context, cluster, values):
        """Create a Node Group from the values dictionary."""
        values = copy.deepcopy(values)
        values = self._populate_node_group(context, values)
        values['tenant_id'] = context.tenant_id
        return self.db.node_group_add(context, cluster, values)

    def node_group_update(self, context, node_group, values):
        """Set the given properties on node_group and update it."""
        values = copy.deepcopy(values)
        self.db.node_group_update(context, node_group, values)

    def node_group_remove(self, context, node_group):
        """Destroy the node_group or raise if it does not exist."""
        self.db.node_group_remove(context, node_group)

    # Instance ops

    def instance_add(self, context, node_group, values):
        """Create an Instance from the values dictionary."""
        values = copy.deepcopy(values)
        values = _apply_defaults(values, INSTANCE_DEFAULTS)
        values['tenant_id'] = context.tenant_id
        return self.db.instance_add(context, node_group, values)

    def instance_update(self, context, instance, values):
        """Set the given properties on Instance and update it."""
        values = copy.deepcopy(values)
        self.db.instance_update(context, instance, values)

    def instance_remove(self, context, instance):
        """Destroy the Instance or raise if it does not exist."""
        self.db.instance_remove(context, instance)

    # Volumes ops

    def append_volume(self, context, instance, volume_id):
        """Append volume_id to instance."""
        self.db.append_volume(context, instance, volume_id)

    def remove_volume(self, context, instance, volume_id):
        """Remove volume_id in instance."""
        self.db.remove_volume(context, instance, volume_id)

    # Cluster Template ops

    def cluster_template_get(self, context, cluster_template):
        """Return the cluster_template or None if it does not exist."""
        return self.db.cluster_template_get(context, cluster_template)

    def cluster_template_get_all(self, context, **kwargs):
        """Get all cluster templates filtered by **kwargs.

        e.g.  cluster_template_get_all(plugin_name='vanilla',
                                       hadoop_version='1.1')
        """
        return self.db.cluster_template_get_all(context, **kwargs)

    def cluster_template_create(self, context, values):
        """Create a cluster_template from the values dictionary."""
        values = copy.deepcopy(values)
        values = _apply_defaults(values, CLUSTER_DEFAULTS)
        values['tenant_id'] = context.tenant_id

        values['node_groups'] = self._populate_node_groups(context, values)

        return self.db.cluster_template_create(context, values)

    def cluster_template_destroy(self, context, cluster_template,
                                 ignore_default=False):
        """Destroy the cluster_template or raise if it does not exist."""
        self.db.cluster_template_destroy(context, cluster_template,
                                         ignore_default)

    def cluster_template_update(self, context, id, values,
                                ignore_default=False):
        """Update a cluster_template from the values dictionary."""
        values = copy.deepcopy(values)
        values = _apply_defaults(values, CLUSTER_DEFAULTS)
        values['tenant_id'] = context.tenant_id
        values['id'] = id

        values['node_groups'] = self._populate_node_groups(context, values)

        return self.db.cluster_template_update(context, values, ignore_default)

    # Node Group Template ops

    def node_group_template_get(self, context, node_group_template):
        """Return the Node Group Template or None if it does not exist."""
        return self.db.node_group_template_get(context, node_group_template)

    def node_group_template_get_all(self, context, **kwargs):
        """Get all NodeGroupTemplates filtered by **kwargs.

        e.g.  node_group_template_get_all(plugin_name='vanilla',
                                          hadoop_version='1.1')
        """
        return self.db.node_group_template_get_all(context, **kwargs)

    def node_group_template_create(self, context, values):
        """Create a Node Group Template from the values dictionary."""
        values = copy.deepcopy(values)
        values = _apply_defaults(values, NODE_GROUP_DEFAULTS)
        values['tenant_id'] = context.tenant_id

        return self.db.node_group_template_create(context, values)

    def node_group_template_destroy(self, context, node_group_template,
                                    ignore_default=False):
        """Destroy the Node Group Template or raise if it does not exist."""
        self.db.node_group_template_destroy(context, node_group_template,
                                            ignore_default)

    def node_group_template_update(self, context, id, values,
                                   ignore_default=False):
        """Update a Node Group Template from the values dictionary."""
        values = copy.deepcopy(values)
        values['tenant_id'] = context.tenant_id
        values['id'] = id

        return self.db.node_group_template_update(context, values,
                                                  ignore_default)

    # Data Source ops

    def data_source_get(self, context, data_source):
        """Return the Data Source or None if it does not exist."""
        return self.db.data_source_get(context, data_source)

    def data_source_get_all(self, context, **kwargs):
        """Get all Data Sources filtered by **kwargs.

        e.g.  data_source_get_all(name='myfile', type='swift')
        """
        return self.db.data_source_get_all(context, **kwargs)

    def data_source_count(self, context, **kwargs):
        """Count Data Sources filtered by **kwargs.

        Uses sqlalchemy "in_" clause for any tuple values
        Uses sqlalchemy "like" clause for any string values containing %
        """
        return self.db.data_source_count(context, **kwargs)

    def data_source_create(self, context, values):
        """Create a Data Source from the values dictionary."""
        values = copy.deepcopy(values)
        values = _apply_defaults(values, DATA_SOURCE_DEFAULTS)
        values['tenant_id'] = context.tenant_id

        return self.db.data_source_create(context, values)

    def data_source_destroy(self, context, data_source):
        """Destroy the Data Source or raise if it does not exist."""
        return self.db.data_source_destroy(context, data_source)

    # JobExecution ops

    def job_execution_get(self, context, job_execution):
        """Return the JobExecution or None if it does not exist."""
        return self.db.job_execution_get(context, job_execution)

    def job_execution_get_all(self, context, **kwargs):
        """Get all JobExecutions filtered by **kwargs.

        kwargs key values may be the names of fields in a JobExecution
        plus the following special values with the indicated meaning:

        'cluster.name' -- name of the Cluster referenced by the JobExecution
        'job.name' -- name of the Job referenced by the JobExecution
        'status' -- JobExecution['info']['status']

        e.g. job_execution_get_all(cluster_id=12, input_id=123)
             job_execution_get_all(**{'cluster.name': 'test',
                                      'job.name': 'wordcount'})
        """
        return self.db.job_execution_get_all(context, **kwargs)

    def job_execution_count(self, context, **kwargs):
        """Count number of JobExecutions filtered by **kwargs.

        e.g. job_execution_count(cluster_id=12, input_id=123)
        """
        return self.db.job_execution_count(context, **kwargs)

    def job_execution_create(self, context, values):
        """Create a JobExecution from the values dictionary."""
        values = copy.deepcopy(values)
        values['tenant_id'] = context.tenant_id
        return self.db.job_execution_create(context, values)

    def job_execution_update(self, context, job_execution, values):
        """Updates a JobExecution from the values dictionary."""
        return self.db.job_execution_update(context, job_execution, values)

    def job_execution_destroy(self, context, job_execution):
        """Destroy the JobExecution or raise if it does not exist."""
        return self.db.job_execution_destroy(context, job_execution)

    # Job ops

    def job_get(self, context, job):
        """Return the Job or None if it does not exist."""
        return self.db.job_get(context, job)

    def job_get_all(self, context, **kwargs):
        """Get all Jobs filtered by **kwargs.

        e.g.  job_get_all(name='myjob', type='MapReduce')
        """
        return self.db.job_get_all(context, **kwargs)

    def job_create(self, context, values):
        """Create a Job from the values dictionary."""
        values = copy.deepcopy(values)
        values['tenant_id'] = context.tenant_id
        return self.db.job_create(context, values)

    def job_update(self, context, job, values):
        """Updates a Job from the values dictionary."""
        return self.db.job_update(context, job, values)

    def job_destroy(self, context, job):
        """Destroy the Job or raise if it does not exist."""
        self.db.job_destroy(context, job)

    # JobBinary ops

    def job_binary_get_all(self, context, **kwargs):
        """Get all JobBinarys filtered by **kwargs.

        e.g.  job_binary_get_all(name='wordcount.jar')
        """
        return self.db.job_binary_get_all(context, **kwargs)

    def job_binary_get(self, context, job_binary_id):
        """Return the JobBinary or None if it does not exist."""
        return self.db.job_binary_get(context, job_binary_id)

    def job_binary_create(self, context, values):
        """Create a JobBinary from the values dictionary."""

        values = copy.deepcopy(values)
        values['tenant_id'] = context.tenant_id
        return self.db.job_binary_create(context, values)

    def job_binary_destroy(self, context, job_binary):
        """Destroy the JobBinary or raise if it does not exist."""
        self.db.job_binary_destroy(context, job_binary)

    # JobBinaryInternal ops

    def job_binary_internal_get_all(self, context, **kwargs):
        """Get all JobBinaryInternals filtered by **kwargs.

        e.g.  cluster_get_all(name='wordcount.jar')

        The JobBinaryInternals returned do not contain a data field.
        """
        return self.db.job_binary_internal_get_all(context, **kwargs)

    def job_binary_internal_get(self, context, job_binary_internal_id):
        """Return the JobBinaryInternal or None if it does not exist

        The JobBinaryInternal returned does not contain a data field.
        """
        return self.db.job_binary_internal_get(context, job_binary_internal_id)

    def job_binary_internal_create(self, context, values):
        """Create a JobBinaryInternal from the values dictionary."""

        # Since values["data"] is (should be) encoded as a string
        # here the deepcopy of values only incs a reference count on data.
        # This is nice, since data could be big...
        values = copy.deepcopy(values)
        values['tenant_id'] = context.tenant_id
        return self.db.job_binary_internal_create(context, values)

    def job_binary_internal_destroy(self, context, job_binary_internal):
        """Destroy the JobBinaryInternal or raise if it does not exist."""
        self.db.job_binary_internal_destroy(context, job_binary_internal)

    def job_binary_internal_get_raw_data(self,
                                         context, job_binary_internal_id):
        """Return the binary data field from a JobBinaryInternal."""
        return self.db.job_binary_internal_get_raw_data(
            context,
            job_binary_internal_id)

    # Events ops

    def cluster_provision_step_add(self, context, cluster_id, values):
        """Create a cluster assigned ProvisionStep

        from the values dictionary
        """
        return self.db.cluster_provision_step_add(context, cluster_id, values)

    def cluster_provision_step_update(self, context, provision_step, values):
        """Update the ProvisionStep from the values dictionary."""
        self.db.cluster_provision_step_update(context, provision_step, values)

    def cluster_provision_step_get_events(self, context, provision_step):
        """Return all events from the specified ProvisionStep."""
        return self.db.cluster_provision_step_get_events(
            context, provision_step)

    def cluster_provision_step_remove_events(self, context, provision_step):
        """Delete all event from the specified ProvisionStep."""
        self.db.cluster_provision_step_remove_events(context, provision_step)

    def cluster_event_add(self, context, provision_step, values):
        """Assign new event to the specified ProvisionStep."""
        self.db.cluster_event_add(context, provision_step, values)
