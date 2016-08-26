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

from oslo_config import cfg

from sahara.conductor import manager
from sahara.conductor import resource as r


conductor_opts = [
    cfg.BoolOpt('use_local',
                default=True,
                help='Perform sahara-conductor operations locally.'),
]

conductor_group = cfg.OptGroup(name='conductor',
                               title='Conductor Options')

CONF = cfg.CONF
CONF.register_group(conductor_group)
CONF.register_opts(conductor_opts, conductor_group)


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
    """A local version of the conductor API.

    It does database updates locally instead of via RPC.
    """

    def __init__(self):
        self._manager = manager.ConductorManager()

    # Cluster ops

    @r.wrap(r.ClusterResource)
    def cluster_get(self, context, cluster, show_progress=False):
        """Return the cluster or None if it does not exist."""
        return self._manager.cluster_get(
            context, _get_id(cluster), show_progress)

    @r.wrap(r.ClusterResource)
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
        return self._manager.cluster_get_all(context, regex_search, **kwargs)

    @r.wrap(r.ClusterResource)
    def cluster_create(self, context, values):
        """Create a cluster from the values dictionary.

        :returns: the created cluster.
        """
        return self._manager.cluster_create(context, values)

    @r.wrap(r.ClusterResource)
    def cluster_update(self, context, cluster, values):
        """Update the cluster with the given values dictionary.

        :returns: the updated cluster.
        """
        return self._manager.cluster_update(context, _get_id(cluster),
                                            values)

    def cluster_destroy(self, context, cluster):
        """Destroy the cluster or raise if it does not exist.

        :returns: None.
        """
        self._manager.cluster_destroy(context, _get_id(cluster))

    # Node Group ops

    def node_group_add(self, context, cluster, values):
        """Create a node group from the values dictionary.

        :returns: ID of the created node group.
        """
        return self._manager.node_group_add(context, _get_id(cluster), values)

    def node_group_update(self, context, node_group, values):
        """Update the node group with the given values dictionary.

        :returns: None.
        """
        self._manager.node_group_update(context, _get_id(node_group), values)

    def node_group_remove(self, context, node_group):
        """Destroy the node group or raise if it does not exist.

        :returns: None.
        """
        self._manager.node_group_remove(context, _get_id(node_group))

    # Instance ops

    def instance_add(self, context, node_group, values):
        """Create an instance from the values dictionary.

        :returns: ID of the created instance.
        """
        return self._manager.instance_add(context, _get_id(node_group), values)

    def instance_update(self, context, instance, values):
        """Update the instance with the given values dictionary.

        :returns: None.
        """
        self._manager.instance_update(context, _get_id(instance), values)

    def instance_remove(self, context, instance):
        """Destroy the instance or raise if it does not exist.

        :returns: None.
        """
        self._manager.instance_remove(context, _get_id(instance))

    # Volumes ops

    def append_volume(self, context, instance, volume_id):
        """Append volume_id to instance."""
        self._manager.append_volume(context, _get_id(instance), volume_id)

    def remove_volume(self, context, instance, volume_id):
        """Remove volume_id in instance."""
        self._manager.remove_volume(context, _get_id(instance), volume_id)

    # Cluster Template ops

    @r.wrap(r.ClusterTemplateResource)
    def cluster_template_get(self, context, cluster_template):
        """Return the cluster template or None if it does not exist."""
        return self._manager.cluster_template_get(context,
                                                  _get_id(cluster_template))

    @r.wrap(r.ClusterTemplateResource)
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
        return self._manager.cluster_template_get_all(context,
                                                      regex_search, **kwargs)

    @r.wrap(r.ClusterTemplateResource)
    def cluster_template_create(self, context, values):
        """Create a cluster template from the values dictionary.

        :returns: the created cluster template
        """
        return self._manager.cluster_template_create(context, values)

    def cluster_template_destroy(self, context, cluster_template,
                                 ignore_prot_on_def=False):
        """Destroy the cluster template or raise if it does not exist.

        :returns: None
        """
        self._manager.cluster_template_destroy(context,
                                               _get_id(cluster_template),
                                               ignore_prot_on_def)

    @r.wrap(r.ClusterTemplateResource)
    def cluster_template_update(self, context, id, cluster_template,
                                ignore_prot_on_def=False):
        """Update the cluster template or raise if it does not exist.

        :returns: the updated cluster template
        """
        return self._manager.cluster_template_update(context,
                                                     id,
                                                     cluster_template,
                                                     ignore_prot_on_def)

    # Node Group Template ops

    @r.wrap(r.NodeGroupTemplateResource)
    def node_group_template_get(self, context, node_group_template):
        """Return the node group template or None if it does not exist."""
        return self._manager.node_group_template_get(
            context, _get_id(node_group_template))

    @r.wrap(r.NodeGroupTemplateResource)
    def node_group_template_get_all(self,
                                    context, regex_search=False, **kwargs):
        """Get all node group templates filtered by **kwargs.

        :param context: The context, and associated authentication, to use with
                        this operation

        :param regex_search: If True, enable regex matching for filter
                             values. See the user guide for more information
                             on how regex matching is handled. If False,
                             no regex matching is done.

        :param kwargs: Specifies values for named fields by which
                       to constrain the search
        """
        return self._manager.node_group_template_get_all(
            context, regex_search, **kwargs)

    @r.wrap(r.NodeGroupTemplateResource)
    def node_group_template_create(self, context, values):
        """Create a node group template from the values dictionary.

        :returns: the created node group template
        """
        return self._manager.node_group_template_create(context, values)

    def node_group_template_destroy(self, context, node_group_template,
                                    ignore_prot_on_def=False):
        """Destroy the node group template or raise if it does not exist.

        :returns: None
        """
        self._manager.node_group_template_destroy(context,
                                                  _get_id(node_group_template),
                                                  ignore_prot_on_def)

    @r.wrap(r.NodeGroupTemplateResource)
    def node_group_template_update(self, context, id, values,
                                   ignore_prot_on_def=False):
        """Update a node group template from the values dictionary.

        :returns: the updated node group template
        """
        return self._manager.node_group_template_update(context, id, values,
                                                        ignore_prot_on_def)

    # Data Source ops

    @r.wrap(r.DataSource)
    def data_source_get(self, context, data_source):
        """Return the Data Source or None if it does not exist."""
        return self._manager.data_source_get(context, _get_id(data_source))

    @r.wrap(r.DataSource)
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
        return self._manager.data_source_get_all(context,
                                                 regex_search, **kwargs)

    def data_source_count(self, context, **kwargs):
        """Count Data Sources filtered by **kwargs.

        Uses sqlalchemy "in_" clause for any tuple values
        Uses sqlalchemy "like" clause for any string values containing %
        """
        return self._manager.data_source_count(context, **kwargs)

    @r.wrap(r.DataSource)
    def data_source_create(self, context, values):
        """Create a Data Source from the values dictionary."""
        return self._manager.data_source_create(context, values)

    def data_source_destroy(self, context, data_source):
        """Destroy the Data Source or raise if it does not exist."""
        self._manager.data_source_destroy(context, _get_id(data_source))

    @r.wrap(r.DataSource)
    def data_source_update(self, context, id, values):
        """Update an existing Data Source"""
        return self._manager.data_source_update(context, id, values)

    # JobExecution ops

    @r.wrap(r.JobExecution)
    def job_execution_get(self, context, job_execution):
        """Return the JobExecution or None if it does not exist."""
        return self._manager.job_execution_get(context,
                                               _get_id(job_execution))

    @r.wrap(r.JobExecution)
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
        return self._manager.job_execution_get_all(context,
                                                   regex_search, **kwargs)

    def job_execution_count(self, context, **kwargs):
        """Count number of JobExecutions filtered by **kwargs.

        e.g. job_execution_count(cluster_id=12, input_id=123)
        """
        return self._manager.job_execution_count(context, **kwargs)

    @r.wrap(r.JobExecution)
    def job_execution_create(self, context, values):
        """Create a JobExecution from the values dictionary."""
        return self._manager.job_execution_create(context, values)

    @r.wrap(r.JobExecution)
    def job_execution_update(self, context, job_execution, values):
        """Update the JobExecution or raise if it does not exist."""
        return self._manager.job_execution_update(context,
                                                  _get_id(job_execution),
                                                  values)

    def job_execution_destroy(self, context, job_execution):
        """Destroy the JobExecution or raise if it does not exist."""
        self._manager.job_execution_destroy(context, _get_id(job_execution))

    # Job ops

    @r.wrap(r.Job)
    def job_get(self, context, job):
        """Return the Job or None if it does not exist."""
        return self._manager.job_get(context, _get_id(job))

    @r.wrap(r.Job)
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
        return self._manager.job_get_all(context, regex_search, **kwargs)

    @r.wrap(r.Job)
    def job_create(self, context, values):
        """Create a Job from the values dictionary."""
        return self._manager.job_create(context, values)

    @r.wrap(r.Job)
    def job_update(self, context, job, values):
        """Update the Job or raise if it does not exist."""
        return self._manager.job_update(context, _get_id(job),
                                        values)

    def job_destroy(self, context, job):
        """Destroy the Job or raise if it does not exist."""
        self._manager.job_destroy(context, _get_id(job))

    def job_main_name(self, context, job):
        """Return the name of the first main JobBinary or None.

        At present the 'mains' element is expected to contain a single element.
        In the future if 'mains' contains more than one element we will need
        a scheme or convention for retrieving a name from the list of binaries.

        :param job: This is expected to be a Job object
        """
        if job.mains:
            binary = self.job_binary_get(context, job.mains[0])
            if binary is not None:
                return binary["name"]
        return None

    def job_lib_names(self, context, job):
        """Return the name of all job lib binaries or an empty list.

        :param job: This is expected to be a Job object
        """
        lib_ids = job.libs or []
        binaries = (self.job_binary_get(context, lib_id) for lib_id in lib_ids)
        return [binary["name"] for binary in binaries if binary is not None]

    # JobBinary ops

    @r.wrap(r.JobBinary)
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
        """
        return self._manager.job_binary_get_all(context,
                                                regex_search, **kwargs)

    @r.wrap(r.JobBinary)
    def job_binary_get(self, context, job_binary):
        """Return the JobBinary or None if it does not exist."""
        return self._manager.job_binary_get(context, _get_id(job_binary))

    @r.wrap(r.JobBinary)
    def job_binary_create(self, context, values):
        """Create a JobBinary from the values dictionary."""
        return self._manager.job_binary_create(context, values)

    def job_binary_destroy(self, context, job_binary):
        """Destroy the JobBinary or raise if it does not exist."""
        self._manager.job_binary_destroy(context, _get_id(job_binary))

    @r.wrap(r.JobBinary)
    def job_binary_update(self, context, id, values):
        """Update a JobBinary from the values dictionary."""
        return self._manager.job_binary_update(context, id, values)

    # JobBinaryInternal ops

    @r.wrap(r.JobBinaryInternal)
    def job_binary_internal_get_all(self, context,
                                    regex_search=False, **kwargs):
        """Get all JobBinaryInternals filtered by **kwargs.

        :param context: The context, and associated authentication, to use with
                        this operation

        :param regex_search: If True, enable regex matching for filter
                             values. See the user guide for more information
                             on how regex matching is handled. If False,
                             no regex matching is done.

        :param kwargs: Specifies values for named fields by which
                       to constrain the search
        """
        return self._manager.job_binary_internal_get_all(
            context, regex_search, **kwargs)

    @r.wrap(r.JobBinaryInternal)
    def job_binary_internal_get(self, context, job_binary_internal):
        """Return the JobBinaryInternal or None if it does not exist."""
        return self._manager.job_binary_internal_get(
            context,
            _get_id(job_binary_internal))

    @r.wrap(r.JobBinaryInternal)
    def job_binary_internal_create(self, context, values):
        """Create a JobBinaryInternal from the values dictionary."""
        return self._manager.job_binary_internal_create(context, values)

    def job_binary_internal_destroy(self, context, job_binary_internal_id):
        """Destroy the JobBinaryInternal or raise if it does not exist."""
        self._manager.job_binary_internal_destroy(
            context,
            _get_id(job_binary_internal_id))

    def job_binary_internal_get_raw_data(self, context,
                                         job_binary_internal_id):
        """Return the binary data field from a JobBinaryInternal."""
        return self._manager.job_binary_internal_get_raw_data(
            context,
            job_binary_internal_id)

    @r.wrap(r.JobBinaryInternal)
    def job_binary_internal_update(self, context, job_binary_internal, values):
        """Update a JobBinaryInternal from the values dictionary."""
        return self._manager.job_binary_internal_update(
            context, _get_id(job_binary_internal), values)

    # Events ops

    def cluster_provision_step_add(self, context, cluster_id, values):
        """Create a provisioning step assigned to cluster from values dict."""
        return self._manager.cluster_provision_step_add(
            context, cluster_id, values)

    def cluster_provision_step_update(self, context, provision_step):
        """Update the cluster provisioning step."""
        return self._manager.cluster_provision_step_update(
            context, provision_step)

    def cluster_provision_progress_update(self, context, cluster_id):
        """Return cluster with provision progress updated field."""
        return self._manager.cluster_provision_progress_update(
            context, cluster_id)

    def cluster_event_add(self, context, provision_step, values):
        """Assign new event to the specified provision step."""
        return self._manager.cluster_event_add(
            context, provision_step, values)

    @r.wrap(r.ClusterVerificationResource)
    def cluster_verification_add(self, context, cluster_id, values):
        """Return created verification for the specified cluster."""
        return self._manager.cluster_verification_add(
            context, _get_id(cluster_id), values)

    @r.wrap(r.ClusterVerificationResource)
    def cluster_verification_get(self, context, verification_id):
        """Return verification with the specified verification_id."""
        return self._manager.cluster_verification_get(
            context, _get_id(verification_id))

    @r.wrap(r.ClusterVerificationResource)
    def cluster_verification_update(self, context, verification_id, values):
        """Return updated verification with the specified verification_id."""
        return self._manager.cluster_verification_update(
            context, _get_id(verification_id), values)

    def cluster_verification_delete(self, context, verification_id):
        """"Delete verification with the specified id."""
        return self._manager.cluster_verification_delete(
            context, _get_id(verification_id))

    @r.wrap(r.ClusterHealthCheckResource)
    def cluster_health_check_add(self, context, verification_id, values):
        """Return created health check in the specified verification."""
        return self._manager.cluster_health_check_add(
            context, _get_id(verification_id), values)

    @r.wrap(r.ClusterHealthCheckResource)
    def cluster_health_check_get(self, context, health_check_id):
        """Return health check with the specified health_check_id."""
        return self._manager.cluster_health_check_get(
            context, _get_id(health_check_id))

    @r.wrap(r.ClusterHealthCheckResource)
    def cluster_health_check_update(self, context, health_check_id, values):
        """Return updated health check with the specified health_check_id."""
        return self._manager.cluster_health_check_update(
            context, _get_id(health_check_id), values)

    def plugin_create(self, context, values):
        """Return created DB entry for plugin."""
        return self._manager.plugin_create(context, values)

    def plugin_get(self, context, name):
        """Return DB entry for plugin."""
        return self._manager.plugin_get(context, name)

    def plugin_get_all(self, context):
        """Return DB entries for all plugins."""
        return self._manager.plugin_get_all(context)

    def plugin_update(self, context, name, values):
        """Return updated DB entry for plugin."""
        return self._manager.plugin_update(context, name, values)

    def plugin_remove(self, context, name):
        """Remove DB entry for plugin."""
        return self._manager.plugin_remove(context, name)


class RemoteApi(LocalApi):
    """Conductor API that does updates via RPC to the ConductorManager."""

    # TODO(slukjanov): it should override _manager and only necessary functions
