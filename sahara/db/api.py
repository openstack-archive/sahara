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

"""Defines interface for DB access.

Functions in this module are imported into the sahara.db namespace. Call these
functions from sahara.db namespace, not the sahara.db.api namespace.

All functions in this module return objects that implement a dictionary-like
interface.

**Related Flags**

:db_backend:  string to lookup in the list of LazyPluggable backends.
              `sqlalchemy` is the only supported backend right now.

:sql_connection:  string specifying the sqlalchemy connection to use, like:
                  `mysql://user:password@localhost/sahara`.

"""

from oslo_config import cfg
from oslo_db import api as db_api
from oslo_db import options
from oslo_log import log as logging

CONF = cfg.CONF

options.set_defaults(CONF)

_BACKEND_MAPPING = {
    'sqlalchemy': 'sahara.db.sqlalchemy.api',
}

IMPL = db_api.DBAPI.from_config(CONF, backend_mapping=_BACKEND_MAPPING)
LOG = logging.getLogger(__name__)


def setup_db():
    """Set up database, create tables, etc.

    Return True on success, False otherwise
    """
    return IMPL.setup_db()


def drop_db():
    """Drop database.

    Return True on success, False otherwise
    """
    return IMPL.drop_db()


# Helpers for building constraints / equality checks


def constraint(**conditions):
    """Return a constraint object suitable for use with some updates."""
    return IMPL.constraint(**conditions)


def equal_any(*values):
    """Return an equality condition object suitable for use in a constraint.

    Equal_any conditions require that a model object's attribute equal any
    one of the given values.
    """
    return IMPL.equal_any(*values)


def not_equal(*values):
    """Return an inequality condition object suitable for use in a constraint.

    Not_equal conditions require that a model object's attribute differs from
    all of the given values.
    """
    return IMPL.not_equal(*values)


def to_dict(func):
    def decorator(*args, **kwargs):
        res = func(*args, **kwargs)

        if isinstance(res, list):
            return [item.to_dict() for item in res]

        if res:
            return res.to_dict()
        else:
            return None

    return decorator


# Cluster ops


def cluster_get(context, cluster, show_progress=False):
    """Return the cluster or None if it does not exist."""
    cluster = IMPL.cluster_get(context, cluster)
    if cluster:
        return cluster.to_dict(show_progress)
    return None


@to_dict
def cluster_get_all(context, **kwargs):
    """Get all clusters filtered by **kwargs.

    e.g. cluster_get_all(ctx, plugin_name='vanilla', hadoop_version='1.1')
    """
    return IMPL.cluster_get_all(context, **kwargs)


@to_dict
def cluster_create(context, values):
    """Create a cluster from the values dictionary."""
    return IMPL.cluster_create(context, values)


@to_dict
def cluster_update(context, cluster, values):
    """Set the given properties on cluster and update it."""
    return IMPL.cluster_update(context, cluster, values)


def cluster_destroy(context, cluster):
    """Destroy the cluster or raise if it does not exist."""
    IMPL.cluster_destroy(context, cluster)


# Node Group ops

def node_group_add(context, cluster, values):
    """Create a Node Group from the values dictionary."""
    return IMPL.node_group_add(context, cluster, values)


def node_group_update(context, node_group, values):
    """Set the given properties on node_group and update it."""
    IMPL.node_group_update(context, node_group, values)


def node_group_remove(context, node_group):
    """Destroy the node_group or raise if it does not exist."""
    IMPL.node_group_remove(context, node_group)


# Instance ops

def instance_add(context, node_group, values):
    """Create an Instance from the values dictionary."""
    return IMPL.instance_add(context, node_group, values)


def instance_update(context, instance, values):
    """Set the given properties on Instance and update it."""
    IMPL.instance_update(context, instance, values)


def instance_remove(context, instance):
    """Destroy the Instance or raise if it does not exist."""
    IMPL.instance_remove(context, instance)


# Volumes ops

def append_volume(context, instance, volume_id):
    """Append volume_id to instance."""
    IMPL.append_volume(context, instance, volume_id)


def remove_volume(context, instance, volume_id):
    """Remove volume_id in instance."""
    IMPL.remove_volume(context, instance, volume_id)


# Cluster Template ops

@to_dict
def cluster_template_get(context, cluster_template):
    """Return the cluster_template or None if it does not exist."""
    return IMPL.cluster_template_get(context, cluster_template)


@to_dict
def cluster_template_get_all(context, **kwargs):
    """Get all cluster templates filtered by **kwargs.

    e.g.  cluster_template_get_all(plugin_name='vanilla',
                                   hadoop_version='1.1')
    """
    return IMPL.cluster_template_get_all(context, **kwargs)


@to_dict
def cluster_template_create(context, values):
    """Create a cluster_template from the values dictionary."""
    return IMPL.cluster_template_create(context, values)


def cluster_template_destroy(context,
                             cluster_template,
                             ignore_default=False):
    """Destroy the cluster_template or raise if it does not exist."""
    IMPL.cluster_template_destroy(context, cluster_template, ignore_default)


@to_dict
def cluster_template_update(context, values, ignore_default=False):
    """Update a cluster_template from the values dictionary."""
    return IMPL.cluster_template_update(context, values, ignore_default)


# Node Group Template ops

@to_dict
def node_group_template_get(context, node_group_template):
    """Return the Node Group Template or None if it does not exist."""
    return IMPL.node_group_template_get(context, node_group_template)


@to_dict
def node_group_template_get_all(context, **kwargs):
    """Get all Node Group Templates filtered by **kwargs.

    e.g.  node_group_template_get_all(plugin_name='vanilla',
                                      hadoop_version='1.1')
    """
    return IMPL.node_group_template_get_all(context, **kwargs)


@to_dict
def node_group_template_create(context, values):
    """Create a Node Group Template from the values dictionary."""
    return IMPL.node_group_template_create(context, values)


def node_group_template_destroy(context,
                                node_group_template,
                                ignore_default=False):
    """Destroy the Node Group Template or raise if it does not exist."""
    IMPL.node_group_template_destroy(context, node_group_template,
                                     ignore_default)


@to_dict
def node_group_template_update(context, node_group_template,
                               ignore_default=False):
    """Update a Node Group Template from the values in a dictionary."""
    return IMPL.node_group_template_update(context, node_group_template,
                                           ignore_default)


# Data Source ops

@to_dict
def data_source_get(context, data_source):
    """Return the Data Source or None if it does not exist."""
    return IMPL.data_source_get(context, data_source)


@to_dict
def data_source_get_all(context, **kwargs):
    """Get all Data Sources filtered by **kwargs.

    e.g.  data_source_get_all(name='myfile', type='swift')
    """
    return IMPL.data_source_get_all(context, **kwargs)


def data_source_count(context, **kwargs):
    """Count Data Sources filtered by **kwargs.

    Uses sqlalchemy "in_" clause for any tuple values
    Uses sqlalchemy "like" clause for any string values containing %
    """
    return IMPL.data_source_count(context, **kwargs)


@to_dict
def data_source_create(context, values):
    """Create a Data Source from the values dictionary."""
    return IMPL.data_source_create(context, values)


def data_source_destroy(context, data_source):
    """Destroy the Data Source or raise if it does not exist."""
    IMPL.data_source_destroy(context, data_source)


# JobExecutions ops

@to_dict
def job_execution_get(context, job_execution):
    """Return the JobExecution or None if it does not exist."""
    return IMPL.job_execution_get(context, job_execution)


@to_dict
def job_execution_get_all(context, **kwargs):
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
    return IMPL.job_execution_get_all(context, **kwargs)


def job_execution_count(context, **kwargs):
    """Count number of JobExecutions filtered by **kwargs.

    e.g. job_execution_count(cluster_id=12, input_id=123)
    """
    return IMPL.job_execution_count(context, **kwargs)


@to_dict
def job_execution_create(context, values):
    """Create a JobExecution from the values dictionary."""
    return IMPL.job_execution_create(context, values)


@to_dict
def job_execution_update(context, job_execution, values):
    """Create a JobExecution from the values dictionary."""
    return IMPL.job_execution_update(context, job_execution, values)


def job_execution_destroy(context, job_execution):
    """Destroy the JobExecution or raise if it does not exist."""
    IMPL.job_execution_destroy(context, job_execution)


# Job ops

@to_dict
def job_get(context, job):
    """Return the Job or None if it does not exist."""
    return IMPL.job_get(context, job)


@to_dict
def job_get_all(context, **kwargs):
    """Get all Jobs filtered by **kwargs.

    e.g.  job_get_all(name='myjob', type='MapReduce')
    """
    return IMPL.job_get_all(context, **kwargs)


@to_dict
def job_create(context, values):
    """Create a Job from the values dictionary."""
    return IMPL.job_create(context, values)


def job_update(context, job, values):
    """Update a Job from the values dictionary."""
    return IMPL.job_update(context, job, values)


def job_destroy(context, job):
    """Destroy the Job or raise if it does not exist."""
    IMPL.job_destroy(context, job)


@to_dict
def job_binary_get_all(context, **kwargs):
    """Get all JobBinarys filtered by **kwargs.

    e.g.  job_binary_get_all(name='wordcount.jar')
    """
    return IMPL.job_binary_get_all(context, **kwargs)


@to_dict
def job_binary_get(context, job_binary):
    """Return the JobBinary or None if it does not exist."""
    return IMPL.job_binary_get(context, job_binary)


@to_dict
def job_binary_create(context, values):
    """Create a JobBinary from the values dictionary."""
    return IMPL.job_binary_create(context, values)


def job_binary_destroy(context, job_binary):
    """Destroy the JobBinary or raise if it does not exist."""
    IMPL.job_binary_destroy(context, job_binary)


@to_dict
def job_binary_internal_get_all(context, **kwargs):
    """Get all JobBinaryInternals filtered by **kwargs.

    e.g.  job_binary_internal_get_all(ctx, name='wordcount.jar')

    The JobBinaryInternals returned do not contain a data field.
    """
    return IMPL.job_binary_internal_get_all(context, **kwargs)


@to_dict
def job_binary_internal_get(context, job_binary_internal):
    """Return the JobBinaryInternal or None if it does not exist."""
    return IMPL.job_binary_internal_get(context, job_binary_internal)


@to_dict
def job_binary_internal_create(context, values):
    """Create a JobBinaryInternal from the values dictionary."""
    return IMPL.job_binary_internal_create(context, values)


def job_binary_internal_destroy(context, job_binary_internal):
    """Destroy the JobBinaryInternal or raise if it does not exist."""
    IMPL.job_binary_internal_destroy(context, job_binary_internal)


def job_binary_internal_get_raw_data(context, job_binary_internal_id):
    """Return the binary data field from the specified JobBinaryInternal."""
    return IMPL.job_binary_internal_get_raw_data(context,
                                                 job_binary_internal_id)


def cluster_provision_step_add(context, cluster_id, values):
    """Create a cluster assigned ProvisionStep from the values dictionary."""
    return IMPL.cluster_provision_step_add(context, cluster_id, values)


def cluster_provision_step_update(context, provision_step, values):
    """Update the ProvisionStep from the values dictionary."""
    IMPL.cluster_provision_step_update(context, provision_step, values)


def cluster_provision_step_get_events(context, provision_step):
    """Return all events from the specified ProvisionStep."""
    return IMPL.cluster_provision_step_get_events(context, provision_step)


def cluster_provision_step_remove_events(context, provision_step):
    """Delete all event from the specified ProvisionStep."""
    IMPL.cluster_provision_step_remove_events(context, provision_step)


def cluster_event_add(context, provision_step, values):
    """Assign new event to the specified ProvisionStep."""
    IMPL.cluster_event_add(context, provision_step, values)
