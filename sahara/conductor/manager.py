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

from oslo_config import cfg

from sahara.conductor import resource as r
from sahara.db import base as db_base
from sahara.service.castellan import utils as key_manager
from sahara.service.edp.utils import shares
from sahara.utils import configs
from sahara.utils import crypto


CONF = cfg.CONF

CLUSTER_DEFAULTS = {
    "cluster_configs": {},
    "status": "undefined",
    "anti_affinity": [],
    "anti_affinity_ratio": 1,
    "status_description": "",
    "info": {},
    "rollback_info": {},
    "sahara_info": {},
    "is_public": False,
    "is_protected": False
}

NODE_GROUP_DEFAULTS = {
    "node_processes": [],
    "node_configs": {},
    "volumes_per_node": 0,
    "volumes_size": 0,
    "volumes_availability_zone": None,
    "volume_mount_prefix": "/volumes/disk",
    "volume_type": None,
    "boot_from_volume": False,
    "boot_volume_type": None,
    "boot_volume_availability_zone": None,
    "boot_volume_local_to_instance": False,
    "floating_ip_pool": None,
    "security_groups": None,
    "auto_security_group": False,
    "availability_zone": None,
    "is_proxy_gateway": False,
    "volume_local_to_instance": False,
}

NODE_GROUP_TEMPLATE_DEFAULTS = copy.deepcopy(NODE_GROUP_DEFAULTS)
NODE_GROUP_TEMPLATE_DEFAULTS.update({"is_public": False,
                                     "is_protected": False})

INSTANCE_DEFAULTS = {
    "volumes": [],
    "storage_devices_number": 0
}

DATA_SOURCE_DEFAULTS = {
    "credentials": {},
    "is_public": False,
    "is_protected": False
}

JOB_DEFAULTS = {
    "is_public": False,
    "is_protected": False
}

JOB_BINARY_DEFAULTS = {
    "is_public": False,
    "is_protected": False
}

JOB_BINARY_INTERNAL_DEFAULTS = {
    "is_public": False,
    "is_protected": False
}

JOB_EXECUTION_DEFAULTS = {
    "is_public": False,
    "is_protected": False
}


def _apply_defaults(values, defaults):
    new_values = copy.deepcopy(defaults)
    new_values.update(values)
    return new_values


class ConductorManager(db_base.Base):
    """This class aimed to conduct things.

    The methods in the base API for sahara-conductor are various proxy
    operations that allow other services to get specific work done without
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

    def cluster_get_all(self, context, regex_search=False, **kwargs):
        """Get all clusters filtered by **kwargs.

        :param context: The context, and associated authentication, to use with
                        this operation

        :param regex_search: If True, enable regex matching for filter
                             values. See the user guide for more information
                             on how regex matching is handled. If False,
                             no regex matching is done.

        :param kwargs: Specifies values for named fields by which
                       to constrain the search
        """
        return self.db.cluster_get_all(context, regex_search, **kwargs)

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
            del c_tmpl['is_public']
            del c_tmpl['is_protected']
            del c_tmpl['tenant_id']

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
        update_shares = values.get('shares')
        if update_shares:
            original_shares = (
                self.db.cluster_get(context, cluster).get('shares', []))

        updated_cluster = self.db.cluster_update(context, cluster, values)
        if update_shares:
            for share in update_shares:
                # Only call mount_shares if we have new shares to mount.
                # We only need one positive case to bother calling mount_shares
                if share not in original_shares:
                    shares.mount_shares(r.ClusterResource(updated_cluster))
                    break
            # Any shares that were on the original, but not on the updated
            # list will be unmounted
            unmount_list = [share for share in original_shares
                            if share not in update_shares]
            if len(unmount_list) > 0:
                shares.unmount_shares(r.ClusterResource(updated_cluster),
                                      unmount_list)

        return updated_cluster

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

    def cluster_template_get_all(self, context, regex_search=False, **kwargs):
        """Get all cluster templates filtered by **kwargs.

        :param context: The context, and associated authentication, to use with
                        this operation

        :param regex_search: If True, enable regex matching for filter
                             values. See the user guide for more information
                             on how regex matching is handled. If False,
                             no regex matching is done.

        :param kwargs: Specifies values for named fields by which
                       to constrain the search
        """
        return self.db.cluster_template_get_all(context,
                                                regex_search, **kwargs)

    def cluster_template_create(self, context, values):
        """Create a cluster_template from the values dictionary."""
        values = copy.deepcopy(values)
        values = _apply_defaults(values, CLUSTER_DEFAULTS)
        values['tenant_id'] = context.tenant_id

        values['node_groups'] = self._populate_node_groups(context, values)

        return self.db.cluster_template_create(context, values)

    def cluster_template_destroy(self, context, cluster_template,
                                 ignore_prot_on_def=False):
        """Destroy the cluster_template or raise if it does not exist."""
        self.db.cluster_template_destroy(context, cluster_template,
                                         ignore_prot_on_def)

    def cluster_template_update(self, context, id, values,
                                ignore_prot_on_def=False):
        """Update a cluster_template from the values dictionary."""
        values = copy.deepcopy(values)
        values['tenant_id'] = context.tenant_id
        values['id'] = id

        if 'node_groups' in values:
            values['node_groups'] = self._populate_node_groups(context, values)

        return self.db.cluster_template_update(context, values,
                                               ignore_prot_on_def)

    # Node Group Template ops

    def node_group_template_get(self, context, node_group_template):
        """Return the Node Group Template or None if it does not exist."""
        return self.db.node_group_template_get(context, node_group_template)

    def node_group_template_get_all(self,
                                    context, regex_search=False, **kwargs):
        """Get all NodeGroupTemplates filtered by **kwargs.

        :param context: The context, and associated authentication, to use with
                        this operation

        :param regex_search: If True, enable regex matching for filter
                             values. See the user guide for more information
                             on how regex matching is handled. If False,
                             no regex matching is done.

        :param kwargs: Specifies values for named fields by which
                       to constrain the search
        """
        return self.db.node_group_template_get_all(context,
                                                   regex_search, **kwargs)

    def node_group_template_create(self, context, values):
        """Create a Node Group Template from the values dictionary."""
        values = copy.deepcopy(values)
        values = _apply_defaults(values, NODE_GROUP_TEMPLATE_DEFAULTS)
        values['tenant_id'] = context.tenant_id

        return self.db.node_group_template_create(context, values)

    def node_group_template_destroy(self, context, node_group_template,
                                    ignore_prot_on_def=False):
        """Destroy the Node Group Template or raise if it does not exist."""
        self.db.node_group_template_destroy(context, node_group_template,
                                            ignore_prot_on_def)

    def node_group_template_update(self, context, id, values,
                                   ignore_prot_on_def=False):
        """Update a Node Group Template from the values dictionary."""
        values = copy.deepcopy(values)
        values['tenant_id'] = context.tenant_id
        values['id'] = id

        return self.db.node_group_template_update(context, values,
                                                  ignore_prot_on_def)

    # Data Source ops

    def data_source_get(self, context, data_source):
        """Return the Data Source or None if it does not exist."""
        return self.db.data_source_get(context, data_source)

    def data_source_get_all(self, context, regex_search=False, **kwargs):
        """Get all Data Sources filtered by **kwargs.

        :param context: The context, and associated authentication, to use with
                        this operation

        :param regex_search: If True, enable regex matching for filter
                             values. See the user guide for more information
                             on how regex matching is handled. If False,
                             no regex matching is done.

        :param kwargs: Specifies values for named fields by which
                       to constrain the search
        """
        return self.db.data_source_get_all(context, regex_search, **kwargs)

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
        # if credentials are being passed in, we use the key_manager
        # to store the password.
        if (values.get('credentials') and
                values['credentials'].get('password')):
            values['credentials']['password'] = key_manager.store_secret(
                values['credentials']['password'], context)
        if (values.get('credentials') and
                values['credentials'].get('secretkey')):
            values['credentials']['secretkey'] = key_manager.store_secret(
                values['credentials']['secretkey'], context)
        return self.db.data_source_create(context, values)

    def data_source_destroy(self, context, data_source):
        """Destroy the Data Source or raise if it does not exist."""

        # in cases where the credentials to access the data source are
        # stored with the record and the external key manager is being
        # used, we need to delete the key from the external manager.
        if (CONF.use_barbican_key_manager and not
                CONF.use_domain_for_proxy_users):
            ds_record = self.data_source_get(context, data_source)
            if (ds_record.get('credentials') and
                    ds_record['credentials'].get('password')):
                key_manager.delete_secret(
                    ds_record['credentials']['password'], context)
        if CONF.use_barbican_key_manager:
            if (ds_record.get('credentials') and
                    ds_record['credentials'].get('secretkey')):
                key_manager.delete_secret(
                    ds_record['credentials']['secretkey'], context)
        return self.db.data_source_destroy(context, data_source)

    def data_source_update(self, context, id, values):
        """Update the Data Source or raise if it does not exist."""

        values = copy.deepcopy(values)
        values["id"] = id
        # in cases where the credentials to access the data source are
        # stored with the record and the external key manager is being
        # used, we need to delete the old key from the manager and
        # create a new one. the other option here would be to retrieve
        # the previous key and check to see if it has changed, but it
        # seems less expensive to just delete the old and create a new
        # one.
        # it should be noted that the jsonschema validation ensures that
        # if the proxy domain is not in use then credentials must be
        # sent with this record.

        # first we retrieve the original record to get the old key
        # uuid, and delete it.
        # next we create the new key.

        if CONF.use_barbican_key_manager:
            ds_record = self.data_source_get(context, id)
            if (ds_record.get('credentials') and
                    ds_record['credentials'].get('password') and
                    not CONF.use_domain_for_proxy_users):
                key_manager.delete_secret(
                    ds_record['credentials']['password'], context)
            if (values.get('credentials') and
                    values['credentials'].get('password') and
                    not CONF.use_domain_for_proxy_users):
                values['credentials']['password'] = key_manager.store_secret(
                    values['credentials']['password'], context)
            if (ds_record.get('credentials') and
                    ds_record['credentials'].get('secretkey')):
                key_manager.delete_secret(
                    ds_record['credentials']['secretkey'], context)
            if (values.get('credentials') and
                    values['credentials'].get('secretkey')):
                values['credentials']['secretkey'] = key_manager.store_secret(
                    values['credentials']['secretkey'], context)
        return self.db.data_source_update(context, values)

    # JobExecution ops

    def job_execution_get(self, context, job_execution):
        """Return the JobExecution or None if it does not exist."""
        return self.db.job_execution_get(context, job_execution)

    def job_execution_get_all(self, context, regex_search=False, **kwargs):
        """Get all JobExecutions filtered by **kwargs.

        kwargs key values may be the names of fields in a JobExecution
        plus the following special values with the indicated meaning:

        'cluster.name' -- name of the Cluster referenced by the JobExecution
        'job.name' -- name of the Job referenced by the JobExecution
        'status' -- JobExecution['info']['status']

        :param context: The context, and associated authentication, to use with
                        this operation

        :param regex_search: If True, enable regex matching for filter
                             values. See the user guide for more information
                             on how regex matching is handled. If False,
                             no regex matching is done.

        :param kwargs: Specifies values for named fields by which
                       to constrain the search
        """
        return self.db.job_execution_get_all(context, regex_search, **kwargs)

    def job_execution_count(self, context, **kwargs):
        """Count number of JobExecutions filtered by **kwargs.

        e.g. job_execution_count(cluster_id=12, input_id=123)
        """
        return self.db.job_execution_count(context, **kwargs)

    def job_execution_create(self, context, values):
        """Create a JobExecution from the values dictionary."""
        values = copy.deepcopy(values)
        values = _apply_defaults(values, JOB_EXECUTION_DEFAULTS)
        values['tenant_id'] = context.tenant_id
        return self.db.job_execution_create(context, values)

    def job_execution_update(self, context, job_execution, values):
        """Updates a JobExecution from the values dictionary."""
        values = copy.deepcopy(values)
        return self.db.job_execution_update(context, job_execution, values)

    def job_execution_destroy(self, context, job_execution):
        """Destroy the JobExecution or raise if it does not exist."""
        return self.db.job_execution_destroy(context, job_execution)

    # Job ops

    def job_get(self, context, job):
        """Return the Job or None if it does not exist."""
        return self.db.job_get(context, job)

    def job_get_all(self, context, regex_search=False, **kwargs):
        """Get all Jobs filtered by **kwargs.

        :param context: The context, and associated authentication, to use with
                        this operation

        :param regex_search: If True, enable regex matching for filter
                             values. See the user guide for more information
                             on how regex matching is handled. If False,
                             no regex matching is done.

        :param kwargs: Specifies values for named fields by which
                       to constrain the search
        """
        return self.db.job_get_all(context, regex_search, **kwargs)

    def job_create(self, context, values):
        """Create a Job from the values dictionary."""
        values = copy.deepcopy(values)
        values = _apply_defaults(values, JOB_DEFAULTS)
        values['tenant_id'] = context.tenant_id
        return self.db.job_create(context, values)

    def job_update(self, context, job, values):
        """Updates a Job from the values dictionary."""
        return self.db.job_update(context, job, values)

    def job_destroy(self, context, job):
        """Destroy the Job or raise if it does not exist."""
        self.db.job_destroy(context, job)

    # JobBinary ops

    def job_binary_get_all(self, context, regex_search=False, **kwargs):
        """Get all JobBinarys filtered by **kwargs.

        :param context: The context, and associated authentication, to use with
                        this operation

        :param regex_search: If True, enable regex matching for filter
                             values. See the user guide for more information
                             on how regex matching is handled. If False,
                             no regex matching is done.

        :param kwargs: Specifies values for named fields by which
                       to constrain the search

        e.g.  job_binary_get_all(name='wordcount.jar')
        """
        return self.db.job_binary_get_all(context,
                                          regex_search, **kwargs)

    def job_binary_get(self, context, job_binary_id):
        """Return the JobBinary or None if it does not exist."""
        return self.db.job_binary_get(context, job_binary_id)

    def job_binary_create(self, context, values):
        """Create a JobBinary from the values dictionary."""

        values = copy.deepcopy(values)
        values = _apply_defaults(values, JOB_BINARY_DEFAULTS)
        values['tenant_id'] = context.tenant_id
        # if credentials are being passed in, we use the key_manager
        # to store the password.
        if values.get('extra') and values['extra'].get('password'):
            values['extra']['password'] = key_manager.store_secret(
                values['extra']['password'], context)
        if values.get('extra') and values['extra'].get('secretkey'):
            values['extra']['secretkey'] = key_manager.store_secret(
                values['extra']['secretkey'], context)
        return self.db.job_binary_create(context, values)

    def job_binary_destroy(self, context, job_binary):
        """Destroy the JobBinary or raise if it does not exist."""

        # in cases where the credentials to access the job binary are
        # stored with the record and the external key manager is being
        # used, we need to delete the key from the external manager.
        if CONF.use_barbican_key_manager:
            jb_record = self.job_binary_get(context, job_binary)
            if not CONF.use_domain_for_proxy_users:
                if (jb_record.get('extra') and
                        jb_record['extra'].get('password')):
                    key_manager.delete_secret(jb_record['extra']['password'],
                                              context)
            if (jb_record.get('extra') and
                    jb_record['extra'].get('secretkey')):
                key_manager.delete_secret(jb_record['extra']['secretkey'],
                                          context)
        self.db.job_binary_destroy(context, job_binary)

    def job_binary_update(self, context, id, values):
        """Update a JobBinary from the values dictionary."""

        values = copy.deepcopy(values)
        values['id'] = id
        # in cases where the credentials to access the job binary are
        # stored with the record and the external key manager is being
        # used, we need to delete the old key from the manager and
        # create a new one. the other option here would be to retrieve
        # the previous key and check to see if it has changed, but it
        # seems less expensive to just delete the old and create a new
        # one.
        if CONF.use_barbican_key_manager:
            # first we retrieve the original record to get the old key
            # uuid, and delete it.
            # next we create the new key.
            jb_record = self.job_binary_get(context, id)
            if not CONF.use_domain_for_proxy_users:
                if (jb_record.get('extra') and
                        jb_record['extra'].get('password')):
                    key_manager.delete_secret(jb_record['extra']['password'],
                                              context)
                if values.get('extra') and values['extra'].get('password'):
                    values['extra']['password'] = key_manager.store_secret(
                        values['extra']['password'], context)
            if jb_record.get('extra') and jb_record['extra'].get('secretkey'):
                key_manager.delete_secret(jb_record['extra']['secretkey'],
                                          context)
            if values.get('extra') and values['extra'].get('secretkey'):
                values['extra']['secretkey'] = key_manager.store_secret(
                    values['extra']['secretkey'], context)
        return self.db.job_binary_update(context, values)

    # JobBinaryInternal ops

    def job_binary_internal_get_all(self, context,
                                    regex_search=False, **kwargs):
        """Get all JobBinaryInternals filtered by **kwargs.

        The JobBinaryInternals returned do not contain a data field.

        :param context: The context, and associated authentication, to use with
                        this operation

        :param regex_search: If True, enable regex matching for filter
                             values. See the user guide for more information
                             on how regex matching is handled. If False,
                             no regex matching is done.

        :param kwargs: Specifies values for named fields by which
                       to constrain the search
        """
        return self.db.job_binary_internal_get_all(context,
                                                   regex_search, **kwargs)

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
        values = _apply_defaults(values, JOB_BINARY_INTERNAL_DEFAULTS)
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

    def job_binary_internal_update(self, context, id, values):
        """Updates a JobBinaryInternal from the values dictionary."""
        return self.db.job_binary_internal_update(context, id, values)

    # Events ops

    def cluster_provision_step_add(self, context, cluster_id, values):
        """Create a provisioning step assigned to cluster from values dict."""
        return self.db.cluster_provision_step_add(context, cluster_id, values)

    def cluster_provision_step_update(self, context, provision_step):
        """Update the cluster provisioning step."""
        return self.db.cluster_provision_step_update(context, provision_step)

    def cluster_provision_progress_update(self, context, cluster_id):
        """Return cluster with provision progress updated field."""
        return self.db.cluster_provision_progress_update(context, cluster_id)

    def cluster_event_add(self, context, provision_step, values):
        """Assign new event to the specified provision step."""
        return self.db.cluster_event_add(context, provision_step, values)

    # Cluster verifications / health checks ops

    def cluster_verification_add(self, context, cluster_id, values):
        """Return created verification for the specified cluster."""
        return self.db.cluster_verification_add(context, cluster_id, values)

    def cluster_verification_get(self, context, verification_id):
        """Return verification with the specified verification_id."""
        return self.db.cluster_verification_get(context, verification_id)

    def cluster_verification_update(self, context, verification_id, values):
        """Return updated verification with the specified verification_id."""
        return self.db.cluster_verification_update(
            context, verification_id, values)

    def cluster_verification_delete(self, context, verification_id):
        """"Delete verification with the specified id."""
        return self.db.cluster_verification_delete(context, verification_id)

    def cluster_health_check_add(self, context, verification_id, values):
        """Return created health check in the specified verification."""
        return self.db.cluster_health_check_add(
            context, verification_id, values)

    def cluster_health_check_get(self, context, health_check_id):
        """Return health check with the specified health_check_id."""
        return self.db.cluster_health_check_get(context, health_check_id)

    def cluster_health_check_update(self, context, health_check_id, values):
        """Return updated health check with the specified health_check_id."""
        return self.db.cluster_health_check_update(
            context, health_check_id, values)

    def plugin_create(self, context, values):
        """Return created DB entry for plugin."""
        return self.db.plugin_create(context, values)

    def plugin_get(self, context, name):
        """Return DB entry for plugin."""
        return self.db.plugin_get(context, name)

    def plugin_get_all(self, context):
        """Return DB entries for all plugins."""
        return self.db.plugin_get_all(context)

    def plugin_update(self, context, name, values):
        """Return updated DB entry for plugin."""
        return self.db.plugin_update(context, name, values)

    def plugin_remove(self, context, name):
        """Remove DB entry for plugin."""
        return self.db.plugin_remove(context, name)
