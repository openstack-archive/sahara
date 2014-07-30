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

from heatclient import exc as heat_exc
from oslo.config import cfg
import six

from sahara import conductor as c
from sahara import context
from sahara.i18n import _LE
from sahara.i18n import _LI
from sahara.i18n import _LW
from sahara.openstack.common import excutils
from sahara.openstack.common import log as logging
from sahara.service import engine as e
from sahara.service import volumes
from sahara.utils import general as g
from sahara.utils.openstack import heat

conductor = c.API
CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class HeatEngine(e.Engine):
    def _add_volumes(self, ctx, cluster):
        for instance in g.get_instances(cluster):
            res_names = heat.client().resources.get(
                cluster.name, instance.instance_name).required_by
            for res_name in res_names:
                vol_res = heat.client().resources.get(cluster.name, res_name)
                if vol_res.resource_type == (('OS::Cinder::'
                                              'VolumeAttachment')):
                    volume_id = vol_res.physical_resource_id
                    conductor.append_volume(ctx, instance, volume_id)

    def create_cluster(self, cluster):
        ctx = context.ctx()

        launcher = _CreateLauncher()

        try:
            target_count = self._get_ng_counts(cluster)
            self._nullify_ng_counts(cluster)

            cluster = conductor.cluster_get(ctx, cluster)
            launcher.launch_instances(ctx, cluster, target_count)

            cluster = conductor.cluster_get(ctx, cluster)
            self._add_volumes(ctx, cluster)

        except Exception as ex:
            with excutils.save_and_reraise_exception():
                if not g.check_cluster_exists(cluster):
                    LOG.info(g.format_cluster_deleted_message(cluster))
                    return
                self._log_operation_exception(
                    _LW("Can't start cluster '%(cluster)s' "
                        "(reason: %(reason)s)"), cluster, ex)

                cluster = g.change_cluster_status(
                    cluster, "Error", status_description=six.text_type(ex))
                self._rollback_cluster_creation(cluster)

    def _get_ng_counts(self, cluster):
        count = {}
        for node_group in cluster.node_groups:
            count[node_group.id] = node_group.count
        return count

    def _nullify_ng_counts(self, cluster):
        ctx = context.ctx()

        for node_group in cluster.node_groups:
            conductor.node_group_update(ctx, node_group, {"count": 0})

    def scale_cluster(self, cluster, target_count):
        ctx = context.ctx()

        rollback_count = self._get_ng_counts(cluster)

        launcher = _ScaleLauncher()

        try:
            launcher.launch_instances(ctx, cluster, target_count)
        except Exception as ex:
            with excutils.save_and_reraise_exception():
                if not g.check_cluster_exists(cluster):
                    LOG.info(g.format_cluster_deleted_message(cluster))
                    return
                self._log_operation_exception(
                    _LW("Can't scale cluster '%(cluster)s' "
                        "(reason: %(reason)s)"), cluster, ex)

                cluster = conductor.cluster_get(ctx, cluster)

                try:
                    self._rollback_cluster_scaling(
                        ctx, cluster, rollback_count, target_count)
                except Exception:
                    if not g.check_cluster_exists(cluster):
                        LOG.info(g.format_cluster_deleted_message(cluster))
                        return
                    # if something fails during the rollback, we stop
                    # doing anything further
                    cluster = g.change_cluster_status(cluster, "Error")
                    LOG.error(_LE("Unable to complete rollback, aborting"))
                    raise

                cluster = g.change_cluster_status(cluster, "Active")
                LOG.warn(
                    _LW("Rollback successful. "
                        "Throwing off an initial exception."))
        finally:
            cluster = conductor.cluster_get(ctx, cluster)
            g.clean_cluster_from_empty_ng(cluster)

        return launcher.inst_ids

    def _populate_cluster(self, ctx, cluster, stack):
        old_ids = [i.instance_id for i in g.get_instances(cluster)]

        new_ids = []

        for node_group in cluster.node_groups:
            nova_ids = stack.get_node_group_instances(node_group)
            for name, nova_id in nova_ids:
                if nova_id not in old_ids:
                    instance_id = conductor.instance_add(
                        ctx, node_group, {"instance_id": nova_id,
                                          "instance_name": name})
                    new_ids.append(instance_id)

        return new_ids

    def _rollback_cluster_creation(self, cluster):
        """Shutdown all instances and update cluster status."""
        LOG.info(_LI("Cluster '%s' creation rollback"), cluster.name)

        self.shutdown_cluster(cluster)

    def _rollback_cluster_scaling(self, ctx, cluster, rollback_count,
                                  target_count):
        """Attempt to rollback cluster scaling.

        Our rollback policy for scaling is as follows:
        We shut down nodes created during scaling, but we don't try to
        to get back decommissioned nodes. I.e. during the rollback
        we only shut down nodes and not launch them. That approach should
        maximize the chance of rollback success.
        """

        LOG.info(_LI("Cluster '%s' scaling rollback"), cluster.name)

        for ng in rollback_count.keys():
            if rollback_count[ng] > target_count[ng]:
                rollback_count[ng] = target_count[ng]

        launcher = _RollbackLauncher()
        launcher.launch_instances(ctx, cluster, rollback_count)

    def shutdown_cluster(self, cluster):
        """Shutdown specified cluster and all related resources."""
        try:
            heat.client().stacks.delete(cluster.name)
            stack = heat.get_stack(cluster.name)
            heat.wait_stack_completion(stack)
        except heat_exc.HTTPNotFound:
            LOG.warn(_LW('Did not found stack for cluster %s') % cluster.name)

        self._clean_job_executions(cluster)

        ctx = context.ctx()
        instances = g.get_instances(cluster)
        for inst in instances:
            conductor.instance_remove(ctx, inst)


class _CreateLauncher(HeatEngine):
    STAGES = ["Spawning", "Waiting", "Preparing"]
    UPDATE_STACK = False
    inst_ids = []

    def launch_instances(self, ctx, cluster, target_count):
        # create all instances
        cluster = g.change_cluster_status(cluster, self.STAGES[0])

        tmpl = heat.ClusterTemplate(cluster)

        self._configure_template(ctx, tmpl, cluster, target_count)
        stack = tmpl.instantiate(update_existing=self.UPDATE_STACK)
        heat.wait_stack_completion(stack.heat_stack)

        self.inst_ids = self._populate_cluster(ctx, cluster, stack)

        # wait for all instances are up and networks ready
        cluster = g.change_cluster_status(cluster, self.STAGES[1])

        instances = g.get_instances(cluster, self.inst_ids)

        self._await_networks(cluster, instances)

        if not g.check_cluster_exists(cluster):
            LOG.info(g.format_cluster_deleted_message(cluster))
            return

        # prepare all instances
        cluster = g.change_cluster_status(cluster, self.STAGES[2])

        instances = g.get_instances(cluster, self.inst_ids)
        volumes.mount_to_instances(instances)

        self._configure_instances(cluster)

    def _configure_template(self, ctx, tmpl, cluster, target_count):
        for node_group in cluster.node_groups:
            count = target_count[node_group.id]
            tmpl.add_node_group_extra(node_group.id, count,
                                      self._generate_user_data_script)

            # if number of instances decreases, we need to drop
            # the excessive ones
            for i in range(count, node_group.count):
                conductor.instance_remove(ctx, node_group.instances[i])


class _ScaleLauncher(_CreateLauncher):
    STAGES = ["Scaling: Spawning", "Scaling: Waiting", "Scaling: Preparing"]
    UPDATE_STACK = True


class _RollbackLauncher(_CreateLauncher):
    STAGES = ["Rollback: Spawning", "Rollback: Waiting", "Rollback: Preparing"]
    UPDATE_STACK = True
