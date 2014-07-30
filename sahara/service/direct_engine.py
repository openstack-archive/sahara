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

from novaclient import exceptions as nova_exceptions
from oslo.config import cfg
import six

from sahara import conductor as c
from sahara import context
from sahara import exceptions as exc
from sahara.i18n import _
from sahara.i18n import _LI
from sahara.i18n import _LW
from sahara.openstack.common import excutils
from sahara.openstack.common import log as logging
from sahara.service import engine as e
from sahara.service import networks
from sahara.service import volumes
from sahara.utils import general as g
from sahara.utils.openstack import nova


conductor = c.API
CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class DirectEngine(e.Engine):
    def create_cluster(self, cluster):
        ctx = context.ctx()
        try:
            # create all instances
            cluster = g.change_cluster_status(cluster, "Spawning")
            self._create_instances(cluster)

            # wait for all instances are up and networks ready
            cluster = g.change_cluster_status(cluster, "Waiting")
            instances = g.get_instances(cluster)

            self._await_active(cluster, instances)

            if not g.check_cluster_exists(cluster):
                LOG.info(g.format_cluster_deleted_message(cluster))
                return

            self._assign_floating_ips(instances)

            self._await_networks(cluster, instances)

            if not g.check_cluster_exists(cluster):
                LOG.info(g.format_cluster_deleted_message(cluster))
                return

            cluster = conductor.cluster_get(ctx, cluster)

            # attach volumes
            volumes.attach_to_instances(g.get_instances(cluster))

            # prepare all instances
            cluster = g.change_cluster_status(cluster, "Preparing")

            self._configure_instances(cluster)
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
                self._rollback_cluster_creation(cluster, ex)

    def scale_cluster(self, cluster, node_group_id_map):
        ctx = context.ctx()

        instance_ids = []
        try:
            instance_ids = self._scale_cluster_instances(cluster,
                                                         node_group_id_map)

            cluster = conductor.cluster_get(ctx, cluster)
            g.clean_cluster_from_empty_ng(cluster)

            cluster = conductor.cluster_get(ctx, cluster)
            instances = g.get_instances(cluster, instance_ids)

            self._await_active(cluster, instances)

            if not g.check_cluster_exists(cluster):
                LOG.info(g.format_cluster_deleted_message(cluster))
                return []

            self._assign_floating_ips(instances)

            self._await_networks(cluster, instances)

            if not g.check_cluster_exists(cluster):
                LOG.info(g.format_cluster_deleted_message(cluster))
                return []

            cluster = conductor.cluster_get(ctx, cluster)

            volumes.attach_to_instances(
                g.get_instances(cluster, instance_ids))

        except Exception as ex:
            with excutils.save_and_reraise_exception():
                if not g.check_cluster_exists(cluster):
                    LOG.info(g.format_cluster_deleted_message(cluster))
                    return []

                self._log_operation_exception(
                    _LW("Can't scale cluster '%(cluster)s' "
                        "(reason: %(reason)s)"), cluster, ex)

                cluster = conductor.cluster_get(ctx, cluster)
                self._rollback_cluster_scaling(
                    cluster, g.get_instances(cluster, instance_ids), ex)
                instance_ids = []

                cluster = conductor.cluster_get(ctx, cluster)
                g.clean_cluster_from_empty_ng(cluster)
                cluster = g.change_cluster_status(cluster, "Active")

        # we should be here with valid cluster: if instances creation
        # was not successful all extra-instances will be removed above
        if instance_ids:
            self._configure_instances(cluster)
        return instance_ids

    def _generate_anti_affinity_groups(self, cluster):
        aa_groups = {}

        for node_group in cluster.node_groups:
            for instance in node_group.instances:
                if instance.instance_id:
                    for process in node_group.node_processes:
                        if process in cluster.anti_affinity:
                            aa_group = aa_groups.get(process, [])
                            aa_group.append(instance.instance_id)
                            aa_groups[process] = aa_group

        return aa_groups

    def _create_instances(self, cluster):
        ctx = context.ctx()

        aa_groups = {}

        for node_group in cluster.node_groups:
            count = node_group.count
            conductor.node_group_update(ctx, node_group, {'count': 0})
            for idx in six.moves.xrange(1, count + 1):
                self._run_instance(cluster, node_group, idx, aa_groups)

    def _scale_cluster_instances(self, cluster, node_group_id_map):
        ctx = context.ctx()
        aa_groups = self._generate_anti_affinity_groups(cluster)
        instances_to_delete = []
        node_groups_to_enlarge = []

        for node_group in cluster.node_groups:
            new_count = node_group_id_map[node_group.id]

            if new_count < node_group.count:
                instances_to_delete += node_group.instances[new_count:
                                                            node_group.count]
            elif new_count > node_group.count:
                node_groups_to_enlarge.append(node_group)

        if instances_to_delete:
            cluster = g.change_cluster_status(cluster, "Deleting Instances")

            for instance in instances_to_delete:
                self._shutdown_instance(instance)

        cluster = conductor.cluster_get(ctx, cluster)

        instances_to_add = []
        if node_groups_to_enlarge:
            cluster = g.change_cluster_status(cluster, "Adding Instances")
            for node_group in node_groups_to_enlarge:
                count = node_group_id_map[node_group.id]
                for idx in six.moves.xrange(node_group.count + 1, count + 1):
                    instance_id = self._run_instance(cluster, node_group, idx,
                                                     aa_groups)
                    instances_to_add.append(instance_id)

        return instances_to_add

    def _find_by_id(self, lst, id):
        for obj in lst:
            if obj.id == id:
                return obj

        return None

    def _run_instance(self, cluster, node_group, idx, aa_groups):
        """Create instance using nova client and persist them into DB."""
        ctx = context.ctx()
        name = g.generate_instance_name(cluster.name, node_group.name, idx)

        userdata = self._generate_user_data_script(node_group, name)

        # aa_groups: node process -> instance ids
        aa_ids = []
        for node_process in node_group.node_processes:
            aa_ids += aa_groups.get(node_process) or []

        # create instances only at hosts w/ no instances
        # w/ aa-enabled processes
        hints = {'different_host': list(set(aa_ids))} if aa_ids else None

        if CONF.use_neutron:
            net_id = cluster.neutron_management_network
            nics = [{"net-id": net_id, "v4-fixed-ip": ""}]

            nova_instance = nova.client().servers.create(
                name, node_group.get_image_id(), node_group.flavor_id,
                scheduler_hints=hints, userdata=userdata,
                key_name=cluster.user_keypair_id,
                nics=nics)
        else:
            nova_instance = nova.client().servers.create(
                name, node_group.get_image_id(), node_group.flavor_id,
                scheduler_hints=hints, userdata=userdata,
                key_name=cluster.user_keypair_id)

        instance_id = conductor.instance_add(ctx, node_group,
                                             {"instance_id": nova_instance.id,
                                              "instance_name": name})
        # save instance id to aa_groups to support aa feature
        for node_process in node_group.node_processes:
            if node_process in cluster.anti_affinity:
                aa_group_ids = aa_groups.get(node_process, [])
                aa_group_ids.append(nova_instance.id)
                aa_groups[node_process] = aa_group_ids

        return instance_id

    def _assign_floating_ips(self, instances):
        for instance in instances:
            node_group = instance.node_group
            if node_group.floating_ip_pool:
                networks.assign_floating_ip(instance.instance_id,
                                            node_group.floating_ip_pool)

    def _await_active(self, cluster, instances):
        """Await all instances are in Active status and available."""
        if not instances:
            return

        active_ids = set()
        while len(active_ids) != len(instances):
            if not g.check_cluster_exists(instances[0].node_group.cluster):
                return
            for instance in instances:
                if instance.id not in active_ids:
                    if self._check_if_active(instance):
                        active_ids.add(instance.id)

            context.sleep(1)

        LOG.info(_LI("Cluster '%s': all instances are active"), cluster.id)

    def _check_if_active(self, instance):

        server = nova.get_instance_info(instance)
        if server.status == 'ERROR':
            raise exc.SystemError(_("Node %s has error status") % server.name)

        return server.status == 'ACTIVE'

    def _rollback_cluster_creation(self, cluster, ex):
        """Shutdown all instances and update cluster status."""
        LOG.info(_LI("Cluster '%(name)s' creation rollback "
                     "(reason: %(reason)s)"),
                 {'name': cluster.name, 'reason': ex})

        self.shutdown_cluster(cluster)

    def _rollback_cluster_scaling(self, cluster, instances, ex):
        """Attempt to rollback cluster scaling."""
        LOG.info(_LI("Cluster '%(name)s' scaling rollback "
                     "(reason: %(reason)s)"),
                 {'name': cluster.name, 'reason': ex})

        for i in instances:
            self._shutdown_instance(i)

    def _shutdown_instances(self, cluster):
        for node_group in cluster.node_groups:
            for instance in node_group.instances:
                self._shutdown_instance(instance)

    def _shutdown_instance(self, instance):
        ctx = context.ctx()

        if instance.node_group.floating_ip_pool:
            try:
                networks.delete_floating_ip(instance.instance_id)
            except nova_exceptions.NotFound:
                LOG.warn(_LW("Attempted to delete non-existent floating IP in "
                         "pool %(pool)s from instance %(instance)s"),
                         {'pool': instance.node_group.floating_ip_pool,
                          'instance': instance.instance_id})

        try:
            volumes.detach_from_instance(instance)
        except Exception:
            LOG.warn(_LW("Detaching volumes from instance %s failed"),
                     instance.instance_id)

        try:
            nova.client().servers.delete(instance.instance_id)
        except nova_exceptions.NotFound:
            LOG.warn(_LW("Attempted to delete non-existent instance %s"),
                     instance.instance_id)

        conductor.instance_remove(ctx, instance)

    def shutdown_cluster(self, cluster):
        """Shutdown specified cluster and all related resources."""
        self._shutdown_instances(cluster)
        self._clean_job_executions(cluster)
