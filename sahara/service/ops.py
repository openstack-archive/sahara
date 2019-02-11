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

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_utils import uuidutils
import six

from sahara import conductor as c
from sahara import context
from sahara import exceptions
from sahara.i18n import _
from sahara.plugins import base as plugin_base
from sahara.plugins import utils as u
from sahara.service.edp import job_manager
from sahara.service.edp.utils import shares
from sahara.service.health import verification_base as ver_base
from sahara.service import ntp_service
from sahara.service import trusts
from sahara.utils import cluster as c_u
from sahara.utils.openstack import nova
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

    def provision_scaled_cluster(self, cluster_id, node_group_id_map,
                                 node_group_instance_map=None):
        context.spawn("cluster-scaling-%s" % cluster_id,
                      _provision_scaled_cluster, cluster_id, node_group_id_map,
                      node_group_instance_map)

    def terminate_cluster(self, cluster_id, force=False):
        context.spawn("cluster-terminating-%s" % cluster_id,
                      terminate_cluster, cluster_id, force)

    def run_edp_job(self, job_execution_id):
        context.spawn("Starting Job Execution %s" % job_execution_id,
                      _run_edp_job, job_execution_id)

    def cancel_job_execution(self, job_execution_id):
        context.spawn("Canceling Job Execution %s" % job_execution_id,
                      _cancel_job_execution, job_execution_id)

    def delete_job_execution(self, job_execution_id):
        context.spawn("Deleting Job Execution %s" % job_execution_id,
                      _delete_job_execution, job_execution_id)

    def handle_verification(self, cluster_id, values):
        context.spawn('Handling Verification for cluster %s' % cluster_id,
                      _handle_verification, cluster_id, values)

    def get_engine_type_and_version(self):
        return INFRA.get_type_and_version()

    def job_execution_suspend(self, job_execution_id):
        context.spawn("Suspend Job Execution %s" % job_execution_id,
                      _suspend_job_execution, job_execution_id)


class RemoteOps(rpc_utils.RPCClient):
    def __init__(self):
        target = messaging.Target(topic='sahara-ops', version='1.0')
        super(RemoteOps, self).__init__(target)

    def provision_cluster(self, cluster_id):
        self.cast('provision_cluster', cluster_id=cluster_id)

    def update_keypair(self, cluster_id):
        self.cast('update_keypair', cluster_id=cluster_id)

    def provision_scaled_cluster(self, cluster_id, node_group_id_map,
                                 node_group_instance_map=None):
        self.cast('provision_scaled_cluster', cluster_id=cluster_id,
                  node_group_id_map=node_group_id_map,
                  node_group_instance_map=node_group_instance_map)

    def terminate_cluster(self, cluster_id, force=False):
        self.cast('terminate_cluster', cluster_id=cluster_id, force=force)

    def run_edp_job(self, job_execution_id):
        self.cast('run_edp_job', job_execution_id=job_execution_id)

    def cancel_job_execution(self, job_execution_id):
        self.cast('cancel_job_execution',
                  job_execution_id=job_execution_id)

    def delete_job_execution(self, job_execution_id):
        self.cast('delete_job_execution',
                  job_execution_id=job_execution_id)

    def handle_verification(self, cluster_id, values):
        self.cast('handle_verification', cluster_id=cluster_id, values=values)

    def get_engine_type_and_version(self):
        return self.call('get_engine_type_and_version')

    def job_execution_suspend(self, job_execution_id):
        self.cast('job_execution_suspend', job_execution_id=job_execution_id)


def request_context(func):
    @functools.wraps(func)
    def wrapped(self, ctx, *args, **kwargs):
        context.set_ctx(context.Context(**ctx))
        return func(self, *args, **kwargs)

    return wrapped


class OpsServer(rpc_utils.RPCServer):
    def __init__(self):
        target = messaging.Target(topic='sahara-ops',
                                  server=uuidutils.generate_uuid(),
                                  version='1.0')
        super(OpsServer, self).__init__(target)

    @request_context
    def provision_cluster(self, cluster_id):
        _provision_cluster(cluster_id)

    @request_context
    def update_keypair(self, cluster_id):
        _update_keypair(cluster_id)

    @request_context
    def provision_scaled_cluster(self, cluster_id, node_group_id_map,
                                 node_group_instance_map=None):
        _provision_scaled_cluster(cluster_id, node_group_id_map,
                                  node_group_instance_map)

    @request_context
    def terminate_cluster(self, cluster_id, force=False):
        terminate_cluster(cluster_id, force)

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
    def handle_verification(self, cluster_id, values):
        _handle_verification(cluster_id, values)

    @request_context
    def get_engine_type_and_version(self):
        return INFRA.get_type_and_version()

    @request_context
    def job_execution_suspend(self, job_execution_id):
        _suspend_job_execution(job_execution_id)


def _setup_trust_for_cluster(cluster):
    cluster = conductor.cluster_get(context.ctx(), cluster)
    trusts.create_trust_for_cluster(cluster)
    trusts.use_os_admin_auth_token(cluster)


def ops_error_handler(description):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(cluster_id, *args, **kwds):
            ctx = context.ctx()
            try:
                # Clearing status description before executing
                c_u.change_cluster_status_description(cluster_id, "")
                f(cluster_id, *args, **kwds)
            except Exception as ex:
                # something happened during cluster operation
                cluster = conductor.cluster_get(ctx, cluster_id)
                # check if cluster still exists (it might have been removed)
                if (cluster is None or
                        cluster.status == c_u.CLUSTER_STATUS_DELETING):
                    LOG.debug("Cluster was deleted or marked for deletion. "
                              "Canceling current operation.")
                    return

                msg = six.text_type(ex)
                LOG.exception("Error during operating on cluster (reason: "
                              "{reason})".format(reason=msg))

                try:
                    # trying to rollback
                    desc = description.format(reason=msg)
                    if _rollback_cluster(cluster, ex):
                        c_u.change_cluster_status(
                            cluster, c_u.CLUSTER_STATUS_ACTIVE, desc)
                    else:
                        c_u.change_cluster_status(
                            cluster, c_u.CLUSTER_STATUS_ERROR, desc)
                except Exception as rex:
                    cluster = conductor.cluster_get(ctx, cluster_id)
                    # check if cluster still exists (it might have been
                    # removed during rollback)
                    if (cluster is None or
                            cluster.status == c_u.CLUSTER_STATUS_DELETING):
                        LOG.debug("Cluster was deleted or marked for deletion."
                                  " Canceling current operation.")
                        return

                    LOG.exception(
                        "Error during rollback of cluster (reason:"
                        " {reason})".format(reason=six.text_type(rex)))
                    desc = "{0}, {1}".format(msg, six.text_type(rex))
                    c_u.change_cluster_status(
                        cluster, c_u.CLUSTER_STATUS_ERROR,
                        description.format(reason=desc))
        return wrapper
    return decorator


def _rollback_cluster(cluster, reason):
    _setup_trust_for_cluster(cluster)
    context.set_step_type(_("Engine: rollback cluster"))
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

    _setup_trust_for_cluster(cluster)

    cluster = conductor.cluster_get(ctx, cluster_id)

    return ctx, cluster, plugin


def _update_sahara_info(ctx, cluster):
    sahara_info = {
        'infrastructure_engine': INFRA.get_type_and_version(),
        'remote': remote.get_remote_type_and_version()}

    return conductor.cluster_update(
        ctx, cluster, {'sahara_info': sahara_info})


@ops_error_handler(
    _("Creating cluster failed for the following reason(s): {reason}"))
def _provision_cluster(cluster_id):
    ctx, cluster, plugin = _prepare_provisioning(cluster_id)

    cluster = _update_sahara_info(ctx, cluster)

    # updating cluster infra
    cluster = c_u.change_cluster_status(
        cluster, c_u.CLUSTER_STATUS_INFRAUPDATING)
    plugin.update_infra(cluster)

    # creating instances and configuring them
    cluster = conductor.cluster_get(ctx, cluster_id)
    context.set_step_type(_("Engine: create cluster"))
    INFRA.create_cluster(cluster)
    ntp_service.configure_ntp(cluster_id)

    # configure cluster
    cluster = c_u.change_cluster_status(
        cluster, c_u.CLUSTER_STATUS_CONFIGURING)
    context.set_step_type(_("Plugin: configure cluster"))
    if hasattr(plugin, 'validate_images'):
        plugin.validate_images(cluster, test_only=False)
    shares.mount_shares(cluster)
    plugin.configure_cluster(cluster)

    # starting prepared and configured cluster
    cluster = c_u.change_cluster_status(
        cluster, c_u.CLUSTER_STATUS_STARTING)

    context.set_step_type(_("Plugin: start cluster"))
    plugin.start_cluster(cluster)

    # cluster is now up and ready
    cluster = c_u.change_cluster_status(
        cluster, c_u.CLUSTER_STATUS_ACTIVE)

    # schedule execution pending job for cluster
    for je in conductor.job_execution_get_all(ctx, cluster_id=cluster.id):
        job_manager.run_job(je.id)

    _refresh_health_for_cluster(cluster_id)


def _specific_inst_to_delete(node_group, node_group_instance_map=None):
    if node_group_instance_map:
        if node_group.id in node_group_instance_map:
            return True
    return False


@ops_error_handler(
    _("Scaling cluster failed for the following reason(s): {reason}"))
def _provision_scaled_cluster(cluster_id, node_group_id_map,
                              node_group_instance_map=None):
    """Provision scaled cluster.

    :param cluster_id: Id of cluster to be scaled.

    :param node_group_id_map: Dictionary in the format
                   node_group_id: number of instances.

    :param node_group_instance_map: Specifies the instances to be removed in
                   each node group.
    """
    ctx, cluster, plugin = _prepare_provisioning(cluster_id)

    # Decommissioning surplus nodes with the plugin
    cluster = c_u.change_cluster_status(
        cluster, c_u.CLUSTER_STATUS_DECOMMISSIONING)

    try:
        instances_to_delete = []
        for node_group in cluster.node_groups:
            ng_inst_to_delete_count = 0
            # new_count is the new number of instance on the current node group
            new_count = node_group_id_map[node_group.id]
            if new_count < node_group.count:
                # Adding selected instances to delete to the list
                if _specific_inst_to_delete(node_group,
                                            node_group_instance_map):
                    for instance_ref in node_group_instance_map[node_group.id]:
                        instances_to_delete.append(_get_instance_obj(
                            node_group.instances, instance_ref))
                        ng_inst_to_delete_count += 1

                # Adding random instances to the list when the number of
                # specific instances does not equals the difference between the
                # current count and the new count of instances.
                while node_group.count - new_count > ng_inst_to_delete_count:
                    instances_to_delete.append(_get_random_instance_from_ng(
                        node_group.instances, instances_to_delete))
                    ng_inst_to_delete_count += 1

        if instances_to_delete:
            context.set_step_type(_("Plugin: decommission cluster"))
            plugin.decommission_nodes(cluster, instances_to_delete)

        # Scaling infrastructure
        cluster = c_u.change_cluster_status(
            cluster, c_u.CLUSTER_STATUS_SCALING)
        context.set_step_type(_("Engine: scale cluster"))
        instance_ids = INFRA.scale_cluster(cluster, node_group_id_map,
                                           instances_to_delete)
        # Setting up new nodes with the plugin
        if instance_ids:
            ntp_service.configure_ntp(cluster_id, instance_ids)
            cluster = c_u.change_cluster_status(
                cluster, c_u.CLUSTER_STATUS_CONFIGURING)
            instances = c_u.get_instances(cluster, instance_ids)
            context.set_step_type(_("Plugin: scale cluster"))
            plugin.scale_cluster(cluster, instances)

        c_u.change_cluster_status(cluster, c_u.CLUSTER_STATUS_ACTIVE)
        _refresh_health_for_cluster(cluster_id)

    except Exception as e:
        c_u.change_cluster_status(cluster, c_u.CLUSTER_STATUS_ACTIVE,
                                  six.text_type(e))


def _get_instance_obj(instances, instance_ref):
    for instance in instances:
        if (instance.instance_id == instance_ref or
                instance.instance_name == instance_ref):
            return instance

    raise exceptions.NotFoundException(str(instance_ref),
                                       _("Instance %s not found"))


def _get_random_instance_from_ng(instances, instances_to_delete):
    # instances list doesn't order by creating date, so we should
    # sort it to make sure deleted instances same as heat deleted.
    insts = sorted(instances,
                   key=lambda x: int(x['instance_name'].split('-')[-1]))
    for instance in reversed(insts):
        if instance not in instances_to_delete:
            return instance


@ops_error_handler(
    _("Terminating cluster failed for the following reason(s): {reason}"))
def terminate_cluster(cluster_id, force=False):
    ctx = context.ctx()
    _setup_trust_for_cluster(cluster_id)

    job_manager.update_job_statuses(cluster_id=cluster_id)
    cluster = conductor.cluster_get(ctx, cluster_id)

    plugin = plugin_base.PLUGINS.get_plugin(cluster.plugin_name)
    context.set_step_type(_("Plugin: shutdown cluster"))
    plugin.on_terminate_cluster(cluster)

    context.set_step_type(_("Engine: shutdown cluster"))
    INFRA.shutdown_cluster(cluster, force)

    trusts.delete_trust_from_cluster(cluster)

    conductor.cluster_destroy(ctx, cluster)


def _run_edp_job(job_execution_id):
    job_manager.run_job(job_execution_id)


def _suspend_job_execution(job_execution_id):
    job_manager.suspend_job(job_execution_id)


def _cancel_job_execution(job_execution_id):
    job_manager.cancel_job(job_execution_id)


def _delete_job_execution(job_execution_id):
    try:
        job_execution = job_manager.cancel_job(job_execution_id)
        if not job_execution:
            # job_execution was deleted already, nothing to do
            return
    except exceptions.CancelingFailed:
        LOG.error("Job execution can't be cancelled in time. "
                  "Deleting it anyway.")
    conductor.job_execution_destroy(context.ctx(), job_execution_id)


def _refresh_health_for_cluster(cluster_id):
    st_dict = {'verification': {'status': 'START'}}
    try:
        ver_base.validate_verification_start(cluster_id)
        ver_base.handle_verification(cluster_id, st_dict)
    except ver_base.CannotVerifyError:
        LOG.debug("Cannot verify cluster because verifications are disabled "
                  "or cluster already is verifying")
    except Exception:
        # if occasional error occurred, there is no reason to move
        # cluster into error state
        LOG.debug("Skipping refreshing cluster health")
        ver_base.clean_verification_data(cluster_id)


def _handle_verification(cluster_id, values):
    ver_base.handle_verification(cluster_id, values)


def _update_keypair(cluster_id):
    ctx = context.ctx()
    cluster = conductor.cluster_get(ctx, cluster_id)
    keypair_name = cluster.user_keypair_id
    key = nova.get_keypair(keypair_name)
    nodes = u.get_instances(cluster)
    for node in nodes:
        with node.remote() as r:
            r.execute_command(
                "echo {keypair} >> ~/.ssh/authorized_keys".
                format(keypair=key.public_key))
