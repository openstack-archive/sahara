# Copyright (c) 2014 Mirantis Inc.
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

import functools
import uuid

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
import six

from sahara import conductor as c
from sahara import context
from sahara import exceptions
from sahara.i18n import _
from sahara.i18n import _LE
from sahara.plugins import base as plugin_base
from sahara.service.edp import job_manager
from sahara.service import trusts
from sahara.utils import general as g
from sahara.utils import remote
from sahara.utils import rpc as rpc_utils


conductor = c.API
CONF = cfg.CONF
LOG = logging.getLogger(__name__)


INFRA = None


def setup_ops(engine):
    global INFRA

    INFRA = engine


class LocalOps(object):
    def provision_cluster(self, cluster_id):
        context.spawn("cluster-creating-%s" % cluster_id,
                      _provision_cluster, cluster_id)

    def provision_scaled_cluster(self, cluster_id, node_group_id_map):
        context.spawn("cluster-scaling-%s" % cluster_id,
                      _provision_scaled_cluster, cluster_id, node_group_id_map)

    def terminate_cluster(self, cluster_id):
        context.spawn("cluster-terminating-%s" % cluster_id,
                      terminate_cluster, cluster_id)

    def run_edp_job(self, job_execution_id):
        context.spawn("Starting Job Execution %s" % job_execution_id,
                      _run_edp_job, job_execution_id)

    def cancel_job_execution(self, job_execution_id):
        context.spawn("Canceling Job Execution %s" % job_execution_id,
                      _cancel_job_execution, job_execution_id)

    def delete_job_execution(self, job_execution_id):
        context.spawn("Deleting Job Execution %s" % job_execution_id,
                      _delete_job_execution, job_execution_id)

    def get_engine_type_and_version(self):
        return INFRA.get_type_and_version()


class RemoteOps(rpc_utils.RPCClient):
    def __init__(self):
        target = messaging.Target(topic='sahara-ops', version='1.0')
        super(RemoteOps, self).__init__(target)

    def provision_cluster(self, cluster_id):
        self.cast('provision_cluster', cluster_id=cluster_id)

    def provision_scaled_cluster(self, cluster_id, node_group_id_map):
        self.cast('provision_scaled_cluster', cluster_id=cluster_id,
                  node_group_id_map=node_group_id_map)

    def terminate_cluster(self, cluster_id):
        self.cast('terminate_cluster', cluster_id=cluster_id)

    def run_edp_job(self, job_execution_id):
        self.cast('run_edp_job', job_execution_id=job_execution_id)

    def cancel_job_execution(self, job_execution_id):
        self.cast('cancel_job_execution',
                  job_execution_id=job_execution_id)

    def delete_job_execution(self, job_execution_id):
        self.cast('delete_job_execution',
                  job_execution_id=job_execution_id)

    def get_engine_type_and_version(self):
        return self.call('get_engine_type_and_version')


def request_context(func):
    @functools.wraps(func)
    def wrapped(self, ctx, *args, **kwargs):
        context.set_ctx(context.Context(**ctx))
        return func(self, *args, **kwargs)

    return wrapped


class OpsServer(rpc_utils.RPCServer):
    def __init__(self):
        target = messaging.Target(topic='sahara-ops', server=uuid.uuid4(),
                                  version='1.0')
        super(OpsServer, self).__init__(target)

    @request_context
    def provision_cluster(self, cluster_id):
        _provision_cluster(cluster_id)

    @request_context
    def provision_scaled_cluster(self, cluster_id, node_group_id_map):
        _provision_scaled_cluster(cluster_id, node_group_id_map)

    @request_context
    def terminate_cluster(self, cluster_id):
        terminate_cluster(cluster_id)

    @request_context
    def run_edp_job(self, job_execution_id):
        _run_edp_job(job_execution_id)

    @request_context
    def cancel_job_execution(self, job_execution_id):
        _cancel_job_execution(job_execution_id)

    @request_context
    def delete_job_execution(self, job_execution_id):
        _delete_job_execution(job_execution_id)

    @request_context
    def get_engine_type_and_version(self):
        return INFRA.get_type_and_version()


def ops_error_handler(description):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(cluster_id, *args, **kwds):
            ctx = context.ctx()
            try:
                # Clearing status description before executing
                g.change_cluster_status_description(cluster_id, "")
                f(cluster_id, *args, **kwds)
            except Exception as ex:
                # something happened during cluster operation
                cluster = conductor.cluster_get(ctx, cluster_id)
                # check if cluster still exists (it might have been removed)
                if cluster is None or cluster.status == 'Deleting':
                    LOG.debug(
                        "Cluster id=%(id)s was deleted or marked for "
                        "deletion. Canceling current operation.",
                        {"id": cluster_id})
                    return

                msg = six.text_type(ex)
                LOG.exception(
                    _LE("Error during operating on cluster {name} (reason: "
                        "{reason})").format(name=cluster.name, reason=msg))

                try:
                    # trying to rollback
                    desc = description.format(reason=msg)
                    if _rollback_cluster(cluster, ex):
                        g.change_cluster_status(cluster, "Active", desc)
                    else:
                        g.change_cluster_status(cluster, "Error", desc)
                except Exception as rex:
                    cluster = conductor.cluster_get(ctx, cluster_id)
                    # check if cluster still exists (it might have been
                    # removed during rollback)
                    if cluster is None or cluster.status == 'Deleting':
                        LOG.debug(
                            "Cluster id=%(id)s was deleted or marked for "
                            "deletion. Canceling current operation.",
                            {"id": cluster_id})
                        return

                    LOG.exception(
                        _LE("Error during rollback of cluster {name} (reason:"
                            " {reason})").format(name=cluster.name,
                                                 reason=six.text_type(rex)))
                    desc = "{0}, {1}".format(msg, six.text_type(rex))
                    g.change_cluster_status(
                        cluster, "Error", description.format(reason=desc))
        return wrapper
    return decorator


def _rollback_cluster(cluster, reason):
    return INFRA.rollback_cluster(cluster, reason)


def _prepare_provisioning(cluster_id):
    ctx = context.ctx()
    cluster = conductor.cluster_get(ctx, cluster_id)
    plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)

    for nodegroup in cluster.node_groups:
        update_dict = {}
        update_dict["image_username"] = INFRA.get_node_group_image_username(
            nodegroup)
        conductor.node_group_update(ctx, nodegroup, update_dict)

    cluster = conductor.cluster_get(ctx, cluster_id)

    return ctx, cluster, plugin


def _update_sahara_info(ctx, cluster):
    sahara_info = {
        'infrastructure_engine': INFRA.get_type_and_version(),
        'remote': remote.get_remote_type_and_version()}

    return conductor.cluster_update(
        ctx, cluster,  {'sahara_info': sahara_info})


@ops_error_handler(
    _("Creating cluster failed for the following reason(s): {reason}"))
def _provision_cluster(cluster_id):
    ctx, cluster, plugin = _prepare_provisioning(cluster_id)

    cluster = _update_sahara_info(ctx, cluster)

    if CONF.use_identity_api_v3 and cluster.is_transient:
        trusts.create_trust_for_cluster(cluster)

    # updating cluster infra
    cluster = g.change_cluster_status(cluster, "InfraUpdating")
    plugin.update_infra(cluster)

    # creating instances and configuring them
    cluster = conductor.cluster_get(ctx, cluster_id)
    INFRA.create_cluster(cluster)

    # configure cluster
    cluster = g.change_cluster_status(cluster, "Configuring")
    plugin.configure_cluster(cluster)

    # starting prepared and configured cluster
    cluster = g.change_cluster_status(cluster, "Starting")
    plugin.start_cluster(cluster)

    # cluster is now up and ready
    cluster = g.change_cluster_status(cluster, "Active")

    # schedule execution pending job for cluster
    for je in conductor.job_execution_get_all(ctx, cluster_id=cluster.id):
        job_manager.run_job(je.id)


@ops_error_handler(
    _("Scaling cluster failed for the following reason(s): {reason}"))
def _provision_scaled_cluster(cluster_id, node_group_id_map):
    ctx, cluster, plugin = _prepare_provisioning(cluster_id)

    # Decommissioning surplus nodes with the plugin
    cluster = g.change_cluster_status(cluster, "Decommissioning")

    instances_to_delete = []

    for node_group in cluster.node_groups:
        new_count = node_group_id_map[node_group.id]
        if new_count < node_group.count:
            instances_to_delete += node_group.instances[new_count:
                                                        node_group.count]

    if instances_to_delete:
        plugin.decommission_nodes(cluster, instances_to_delete)

    # Scaling infrastructure
    cluster = g.change_cluster_status(cluster, "Scaling")

    instance_ids = INFRA.scale_cluster(cluster, node_group_id_map)

    # Setting up new nodes with the plugin
    if instance_ids:
        cluster = g.change_cluster_status(cluster, "Configuring")
        instances = g.get_instances(cluster, instance_ids)
        plugin.scale_cluster(cluster, instances)

    g.change_cluster_status(cluster, "Active")


@ops_error_handler(
    _("Terminating cluster failed for the following reason(s): {reason}"))
def terminate_cluster(cluster_id):
    ctx = context.ctx()
    cluster = conductor.cluster_get(ctx, cluster_id)
    plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)

    plugin.on_terminate_cluster(cluster)

    INFRA.shutdown_cluster(cluster)

    if CONF.use_identity_api_v3:
        trusts.delete_trust_from_cluster(cluster)

    conductor.cluster_destroy(ctx, cluster)


def _run_edp_job(job_execution_id):
    job_manager.run_job(job_execution_id)


def _cancel_job_execution(job_execution_id):
    job_manager.cancel_job(job_execution_id)


def _delete_job_execution(job_execution_id):
    try:
        job_execution = job_manager.cancel_job(job_execution_id)
        if not job_execution:
            # job_execution was deleted already, nothing to do
            return
    except exceptions.CancelingFailed:
        LOG.error(_LE("Job execution %s can't be cancelled in time. "
                      "Deleting it anyway."), job_execution_id)
    conductor.job_execution_destroy(context.ctx(), job_execution_id)
