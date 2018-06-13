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
from oslo_config import cfg
from oslo_log import log as logging

from sahara import conductor as c
from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.service import engine as e
from sahara.service.heat import commons as heat_common
from sahara.service.heat import templates as ht
from sahara.service import volumes
from sahara.utils import cluster as c_u
from sahara.utils import cluster_progress_ops as cpo
from sahara.utils.openstack import heat

conductor = c.API
CONF = cfg.CONF
LOG = logging.getLogger(__name__)

CREATE_STAGES = [c_u.CLUSTER_STATUS_SPAWNING, c_u.CLUSTER_STATUS_WAITING,
                 c_u.CLUSTER_STATUS_PREPARING]
SCALE_STAGES = [c_u.CLUSTER_STATUS_SCALING_SPAWNING,
                c_u.CLUSTER_STATUS_SCALING_WAITING,
                c_u.CLUSTER_STATUS_SCALING_PREPARING]
ROLLBACK_STAGES = [c_u.CLUSTER_STATUS_ROLLBACK_SPAWNING,
                   c_u.CLUSTER_STATUS_ROLLBACK_WAITING,
                   c_u.CLUSTER_STATUS_ROLLBACK__PREPARING]

heat_engine_opts = [
    cfg.ListOpt('heat_stack_tags', default=['data-processing-cluster'],
                help="List of tags to be used during operating with stack.")
]

CONF.register_opts(heat_engine_opts)


class HeatEngine(e.Engine):
    def get_type_and_version(self):
        return heat_common.HEAT_ENGINE_VERSION

    def create_cluster(self, cluster):
        self._update_rollback_strategy(cluster, shutdown=True)

        target_count = self._get_ng_counts(cluster)
        self._nullify_ng_counts(cluster)
        cluster = self._generate_heat_stack_name(cluster)
        self._launch_instances(cluster, target_count, CREATE_STAGES)

        self._update_rollback_strategy(cluster)

    @staticmethod
    def _generate_heat_stack_name(cluster):
        cluster = conductor.cluster_get(context.ctx(), cluster)
        hsn = cluster.name + cluster.id[:8]
        extra = cluster.extra.to_dict() if cluster.extra else {}
        extra['heat_stack_name'] = hsn
        conductor.cluster_update(context.ctx(), cluster, {'extra': extra})
        return conductor.cluster_get(context.ctx(), cluster)

    def _get_ng_counts(self, cluster):
        count = {}
        for node_group in cluster.node_groups:
            count[node_group.id] = node_group.count
        return count

    def _nullify_ng_counts(self, cluster):
        ctx = context.ctx()

        for node_group in cluster.node_groups:
            conductor.node_group_update(ctx, node_group, {"count": 0})

    def scale_cluster(self, cluster, target_count, instances_to_delete=None):
        ctx = context.ctx()

        rollback_count = self._get_ng_counts(cluster)

        self._update_rollback_strategy(cluster, rollback_count=rollback_count,
                                       target_count=target_count)

        inst_ids = self._launch_instances(
            cluster, target_count, SCALE_STAGES,
            update_stack=True, disable_rollback=False,
            instances_to_delete=instances_to_delete)

        cluster = conductor.cluster_get(ctx, cluster)
        c_u.clean_cluster_from_empty_ng(cluster)

        self._update_rollback_strategy(cluster)

        return inst_ids

    def rollback_cluster(self, cluster, reason):
        rollback_info = cluster.rollback_info or {}
        self._update_rollback_strategy(cluster)

        if rollback_info.get('shutdown', False):
            self._rollback_cluster_creation(cluster, reason)
            LOG.warning("Cluster creation rollback "
                        "(reason: {reason})".format(reason=reason))

            return False

        rollback_count = rollback_info.get('rollback_count', {}).copy()
        target_count = rollback_info.get('target_count', {}).copy()
        if rollback_count or target_count:
            self._rollback_cluster_scaling(
                cluster, rollback_count, target_count, reason)
            LOG.warning("Cluster scaling rollback "
                        "(reason: {reason})".format(reason=reason))

            return True

        return False

    def _update_rollback_strategy(self, cluster, shutdown=False,
                                  rollback_count=None, target_count=None):
        rollback_info = {}

        if shutdown:
            rollback_info['shutdown'] = shutdown

        if rollback_count:
            rollback_info['rollback_count'] = rollback_count

        if target_count:
            rollback_info['target_count'] = target_count

        cluster = conductor.cluster_update(
            context.ctx(), cluster, {'rollback_info': rollback_info})
        return cluster

    def _populate_cluster(self, cluster, stack):
        ctx = context.ctx()
        old_ids = [i.instance_id for i in c_u.get_instances(cluster)]
        new_ids = []

        for node_group in cluster.node_groups:
            instances = stack.get_node_group_instances(node_group)
            for instance in instances:
                nova_id = instance['physical_id']
                if nova_id not in old_ids:
                    name = instance['name']
                    inst = {
                        "instance_id": nova_id,
                        "instance_name": name
                    }
                    if cluster.use_designate_feature():
                        inst.update(
                            {"dns_hostname":
                                name + '.' + cluster.domain_name[:-1]})
                    instance_id = conductor.instance_add(ctx, node_group, inst)
                    new_ids.append(instance_id)

        return new_ids

    def _rollback_cluster_creation(self, cluster, ex):
        """Shutdown all instances and update cluster status."""

        self.shutdown_cluster(cluster)

    def _rollback_cluster_scaling(self, cluster, rollback_count,
                                  target_count, ex):
        """Attempt to rollback cluster scaling.

        Our rollback policy for scaling is as follows:
        We shut down nodes created during scaling, but we don't try to
        to get back decommissioned nodes. I.e. during the rollback
        we only shut down nodes and not launch them. That approach should
        maximize the chance of rollback success.
        """

        for ng in rollback_count:
            if rollback_count[ng] > target_count[ng]:
                rollback_count[ng] = target_count[ng]

        self._launch_instances(cluster, rollback_count, ROLLBACK_STAGES,
                               update_stack=True)

    def shutdown_cluster(self, cluster, force=False):
        """Shutdown specified cluster and all related resources."""
        if force:
            heat_shutdown = heat.lazy_delete_stack
        else:
            heat_shutdown = heat.delete_stack

        try:
            heat_shutdown(cluster)
        except heat_exc.HTTPNotFound:
            LOG.warning('Did not find stack for cluster.')
        except ex.HeatStackException:
            raise

        self._clean_job_executions(cluster)
        self._remove_db_objects(cluster)

    @cpo.event_wrapper(
        True, step=_('Create Heat stack'), param=('cluster', 1))
    def _create_instances(self, cluster, target_count, update_stack=False,
                          disable_rollback=True, instances_to_delete=None):

        stack = ht.ClusterStack(cluster)

        self._update_instance_count(stack, cluster, target_count,
                                    instances_to_delete)
        stack.instantiate(update_existing=update_stack,
                          disable_rollback=disable_rollback)
        heat.wait_stack_completion(
            cluster, is_update=update_stack,
            last_updated_time=stack.last_updated_time)
        return self._populate_cluster(cluster, stack)

    def _launch_instances(self, cluster, target_count, stages,
                          update_stack=False, disable_rollback=True,
                          instances_to_delete=None):
        # create all instances
        cluster = c_u.change_cluster_status(cluster, stages[0])

        inst_ids = self._create_instances(
            cluster, target_count, update_stack, disable_rollback,
            instances_to_delete)

        # wait for all instances are up and networks ready
        cluster = c_u.change_cluster_status(cluster, stages[1])

        instances = c_u.get_instances(cluster, inst_ids)

        self._await_networks(cluster, instances)

        # prepare all instances
        cluster = c_u.change_cluster_status(cluster, stages[2])

        instances = c_u.get_instances(cluster, inst_ids)

        volumes.mount_to_instances(instances)

        self._configure_instances(cluster)

        return inst_ids

    def _update_instance_count(self, stack, cluster, target_count,
                               instances_to_delete=None):
        ctx = context.ctx()
        instances_name_to_delete = {}
        if instances_to_delete:
            for instance in instances_to_delete:
                node_group_id = instance['node_group']['id']
                if node_group_id not in instances_name_to_delete:
                    instances_name_to_delete[node_group_id] = []
                instances_name_to_delete[node_group_id].append(
                    instance['instance_name'])

        for node_group in cluster.node_groups:
            count = target_count[node_group.id]
            stack.add_node_group_extra(
                node_group.id, count, self._generate_user_data_script,
                instances_name_to_delete.get(node_group.id, None))

            for inst in node_group.instances:
                if (instances_to_delete and
                        node_group.id in instances_name_to_delete):
                    if (inst.instance_name in
                            instances_name_to_delete[node_group.id]):
                        conductor.instance_remove(ctx, inst)
