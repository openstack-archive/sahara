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
from sahara.i18n import _LE
from sahara.i18n import _LI
from sahara.i18n import _LW
from sahara.openstack.common import log as logging
from sahara.service import engine as e
from sahara.service import networks
from sahara.service import volumes
from sahara.utils import general as g
from sahara.utils.openstack import neutron
from sahara.utils.openstack import nova


conductor = c.API
CONF = cfg.CONF
LOG = logging.getLogger(__name__)

SSH_PORT = 22


class DirectEngine(e.Engine):
    def get_type_and_version(self):
        return "direct.1.0"

    def create_cluster(self, cluster):
        ctx = context.ctx()
        self._update_rollback_strategy(cluster, shutdown=True)

        # create all instances
        cluster = g.change_cluster_status(cluster, "Spawning")
        self._create_instances(cluster)

        # wait for all instances are up and networks ready
        cluster = g.change_cluster_status(cluster, "Waiting")
        instances = g.get_instances(cluster)

        self._await_active(cluster, instances)

        self._assign_floating_ips(instances)

        self._await_networks(cluster, instances)

        cluster = conductor.cluster_get(ctx, cluster)

        # attach volumes
        volumes.attach_to_instances(g.get_instances(cluster))

        # prepare all instances
        cluster = g.change_cluster_status(cluster, "Preparing")

        self._configure_instances(cluster)

        self._update_rollback_strategy(cluster)

    def scale_cluster(self, cluster, node_group_id_map):
        ctx = context.ctx()
        cluster = g.change_cluster_status(cluster, "Scaling")

        instance_ids = self._scale_cluster_instances(cluster,
                                                     node_group_id_map)

        self._update_rollback_strategy(cluster, instance_ids=instance_ids)

        cluster = conductor.cluster_get(ctx, cluster)
        g.clean_cluster_from_empty_ng(cluster)

        cluster = conductor.cluster_get(ctx, cluster)
        instances = g.get_instances(cluster, instance_ids)

        self._await_active(cluster, instances)

        self._assign_floating_ips(instances)

        self._await_networks(cluster, instances)

        cluster = conductor.cluster_get(ctx, cluster)

        volumes.attach_to_instances(
            g.get_instances(cluster, instance_ids))

        # we should be here with valid cluster: if instances creation
        # was not successful all extra-instances will be removed above
        if instance_ids:
            self._configure_instances(cluster)

        self._update_rollback_strategy(cluster)

        return instance_ids

    def rollback_cluster(self, cluster, reason):
        rollback_info = cluster.rollback_info or {}
        self._update_rollback_strategy(cluster)

        if rollback_info.get('shutdown', False):
            self._rollback_cluster_creation(cluster, reason)
            return False

        instance_ids = rollback_info.get('instance_ids', [])
        if instance_ids:
            self._rollback_cluster_scaling(
                cluster, g.get_instances(cluster, instance_ids), reason)

            return True

        return False

    def _update_rollback_strategy(self, cluster, shutdown=False,
                                  instance_ids=None):
        rollback_info = {}
        if shutdown:
            rollback_info['shutdown'] = shutdown

        if instance_ids:
            rollback_info['instance_ids'] = instance_ids

        cluster = conductor.cluster_update(
            context.ctx(), cluster, {'rollback_info': rollback_info})
        return cluster

    # TODO(alazarev) remove when we fully switch to server groups
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

        cluster = self._create_auto_security_groups(cluster)

        aa_group = None
        if cluster.anti_affinity:
            aa_group = self._create_aa_server_group(cluster)

        for node_group in cluster.node_groups:
            count = node_group.count
            conductor.node_group_update(ctx, node_group, {'count': 0})
            for idx in six.moves.xrange(1, count + 1):
                self._run_instance(cluster, node_group, idx, aa_group=aa_group)

    def _create_aa_server_group(self, cluster):
        server_group_name = g.generate_aa_group_name(cluster.name)
        client = nova.client().server_groups

        if client.findall(name=server_group_name):
            raise exc.InvalidDataException(
                _("Server group with name %s is already exists")
                % server_group_name)

        server_group = client.create(name=server_group_name,
                                     policies=['anti-affinity'])
        return server_group.id

    def _delete_aa_server_group(self, cluster):
        if cluster.anti_affinity:
            server_group_name = g.generate_aa_group_name(cluster.name)
            client = nova.client().server_groups

            server_groups = client.findall(name=server_group_name)
            if len(server_groups) == 1:
                client.delete(server_groups[0].id)

    def _find_aa_server_group(self, cluster):
        server_group_name = g.generate_aa_group_name(cluster.name)
        server_groups = nova.client().server_groups.findall(
            name=server_group_name)

        if len(server_groups) > 1:
            raise exc.IncorrectStateError(
                _("Several server groups with name %s found")
                % server_group_name)

        if len(server_groups) == 1:
            return server_groups[0].id

        return None

    def _create_auto_security_groups(self, cluster):
        ctx = context.ctx()
        for node_group in cluster.node_groups:
            if node_group.auto_security_group:
                self._create_auto_security_group(node_group)

        return conductor.cluster_get(ctx, cluster)

    def _scale_cluster_instances(self, cluster, node_group_id_map):
        ctx = context.ctx()

        aa_group = None
        old_aa_groups = None
        if cluster.anti_affinity:
            aa_group = self._find_aa_server_group(cluster)
            if not aa_group:
                old_aa_groups = self._generate_anti_affinity_groups(cluster)

        instances_to_delete = []
        node_groups_to_enlarge = set()
        node_groups_to_delete = set()

        for node_group in cluster.node_groups:
            new_count = node_group_id_map[node_group.id]

            if new_count < node_group.count:
                instances_to_delete += node_group.instances[new_count:
                                                            node_group.count]
                if new_count == 0:
                    node_groups_to_delete.add(node_group.id)
            elif new_count > node_group.count:
                node_groups_to_enlarge.add(node_group.id)
                if node_group.count == 0 and node_group.auto_security_group:
                    self._create_auto_security_group(node_group)

        if instances_to_delete:
            cluster = g.change_cluster_status(cluster, "Deleting Instances")

            for instance in instances_to_delete:
                self._shutdown_instance(instance)

        self._await_deleted(cluster, instances_to_delete)
        for ng in cluster.node_groups:
            if ng.id in node_groups_to_delete:
                self._delete_auto_security_group(ng)

        cluster = conductor.cluster_get(ctx, cluster)
        instances_to_add = []
        if node_groups_to_enlarge:
            cluster = g.change_cluster_status(cluster, "Adding Instances")
            for ng in cluster.node_groups:
                if ng.id in node_groups_to_enlarge:
                    count = node_group_id_map[ng.id]
                    for idx in six.moves.xrange(ng.count + 1, count + 1):
                        instance_id = self._run_instance(
                            cluster, ng, idx,
                            aa_group=aa_group, old_aa_groups=old_aa_groups)
                        instances_to_add.append(instance_id)

        return instances_to_add

    def _map_security_groups(self, security_groups):
        if not security_groups:
            # Nothing to do here
            return None

        if CONF.use_neutron:
            # When using Neutron, ids work fine.
            return security_groups
        else:
            # Nova Network requires that security groups are passed by names.
            # security_groups.get method accepts both ID and names, so in case
            # IDs are provided they will be converted, otherwise the names will
            # just map to themselves.
            names = []
            for group_id_or_name in security_groups:
                group = nova.client().security_groups.get(group_id_or_name)
                names.append(group.name)
            return names

    def _run_instance(self, cluster, node_group, idx, aa_group=None,
                      old_aa_groups=None):
        """Create instance using nova client and persist them into DB."""
        ctx = context.ctx()
        name = g.generate_instance_name(cluster.name, node_group.name, idx)

        userdata = self._generate_user_data_script(node_group, name)

        if old_aa_groups:
            # aa_groups: node process -> instance ids
            aa_ids = []
            for node_process in node_group.node_processes:
                aa_ids += old_aa_groups.get(node_process) or []

            # create instances only at hosts w/ no instances
            # w/ aa-enabled processes
            hints = {'different_host': sorted(set(aa_ids))} if aa_ids else None
        else:
            hints = {'group': aa_group} if (
                aa_group and self._need_aa_server_group(node_group)) else None

        security_groups = self._map_security_groups(node_group.security_groups)
        nova_kwargs = {'scheduler_hints': hints, 'userdata': userdata,
                       'key_name': cluster.user_keypair_id,
                       'security_groups': security_groups}

        if CONF.use_neutron:
            net_id = cluster.neutron_management_network
            nova_kwargs['nics'] = [{"net-id": net_id, "v4-fixed-ip": ""}]

        nova_instance = nova.client().servers.create(name,
                                                     node_group.get_image_id(),
                                                     node_group.flavor_id,
                                                     **nova_kwargs)
        instance_id = conductor.instance_add(ctx, node_group,
                                             {"instance_id": nova_instance.id,
                                              "instance_name": name})

        if old_aa_groups:
            # save instance id to aa_groups to support aa feature
            for node_process in node_group.node_processes:
                if node_process in cluster.anti_affinity:
                    aa_group_ids = old_aa_groups.get(node_process, [])
                    aa_group_ids.append(nova_instance.id)
                    old_aa_groups[node_process] = aa_group_ids

        return instance_id

    def _create_auto_security_group(self, node_group):
        name = g.generate_auto_security_group_name(node_group)
        nova_client = nova.client()
        security_group = nova_client.security_groups.create(
            name, "Auto security group created by Sahara for Node Group '%s' "
                  "of cluster '%s'." %
                  (node_group.name, node_group.cluster.name))

        # ssh remote needs ssh port, agents are not implemented yet
        nova_client.security_group_rules.create(
            security_group.id, 'tcp', SSH_PORT, SSH_PORT, "0.0.0.0/0")

        # open all traffic for private networks
        if CONF.use_neutron:
            for cidr in neutron.get_private_network_cidrs(node_group.cluster):
                for protocol in ['tcp', 'udp']:
                    nova_client.security_group_rules.create(
                        security_group.id, protocol, 1, 65535, cidr)

                nova_client.security_group_rules.create(
                    security_group.id, 'icmp', -1, -1, cidr)

        # enable ports returned by plugin
        for port in node_group.open_ports:
            nova_client.security_group_rules.create(
                security_group.id, 'tcp', port, port, "0.0.0.0/0")

        security_groups = list(node_group.security_groups or [])
        security_groups.append(security_group.id)
        conductor.node_group_update(context.ctx(), node_group,
                                    {"security_groups": security_groups})
        return security_groups

    def _need_aa_server_group(self, node_group):
        for node_process in node_group.node_processes:
            if node_process in node_group.cluster.anti_affinity:
                return True
        return False

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
            if not g.check_cluster_exists(cluster):
                return
            for instance in instances:
                if instance.id not in active_ids:
                    if self._check_if_active(instance):
                        active_ids.add(instance.id)

            context.sleep(1)

        LOG.info(_LI("Cluster '%s': all instances are active"), cluster.id)

    def _await_deleted(self, cluster, instances):
        """Await all instances are deleted."""
        if not instances:
            return

        deleted_ids = set()
        while len(deleted_ids) != len(instances):
            if not g.check_cluster_exists(cluster):
                return
            for instance in instances:
                if instance.id not in deleted_ids:
                    if self._check_if_deleted(instance):
                        LOG.debug("Instance '%s' is deleted" %
                                  instance.instance_name)
                        deleted_ids.add(instance.id)

            context.sleep(1)

    def _check_if_active(self, instance):
        server = nova.get_instance_info(instance)
        if server.status == 'ERROR':
            raise exc.SystemError(_("Node %s has error status") % server.name)

        return server.status == 'ACTIVE'

    def _check_if_deleted(self, instance):
        try:
            nova.get_instance_info(instance)
        except nova_exceptions.NotFound:
            return True

        return False

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

        cluster = conductor.cluster_get(context.ctx(), cluster)
        g.clean_cluster_from_empty_ng(cluster)

    def _shutdown_instances(self, cluster):
        for node_group in cluster.node_groups:
            for instance in node_group.instances:
                self._shutdown_instance(instance)

            self._await_deleted(cluster, node_group.instances)
            self._delete_auto_security_group(node_group)

    def _delete_auto_security_group(self, node_group):
        if not node_group.auto_security_group:
            return

        if not node_group.security_groups:
            # node group has no security groups
            # nothing to delete
            return

        name = node_group.security_groups[-1]

        try:
            client = nova.client().security_groups
            security_group = client.get(name)
            if (security_group.name !=
                    g.generate_auto_security_group_name(node_group)):
                LOG.warn(_LW("Auto security group for node group %s is not "
                             "found"), node_group.name)
                return
            client.delete(name)
        except Exception:
            LOG.exception(_LE("Failed to delete security group %s"), name)

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
        self._delete_aa_server_group(cluster)
