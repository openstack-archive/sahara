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

import datetime

from heatclient import exc as heat_exc
from oslo.config import cfg
import six

from savanna import conductor as c
from savanna import context
from savanna.openstack.common import excutils
from savanna.openstack.common import log as logging
from savanna.service import networks
from savanna.service import volumes_heat as volumes
from savanna.utils import general as g
from savanna.utils.openstack import heat


conductor = c.API
CONF = cfg.CONF
LOG = logging.getLogger(__name__)

CLOUD_INIT_USERNAME = 'ec2-user'


class HeatInfrastructureEngine(object):
    def create_cluster(self, cluster):
        _create_cluster(cluster)

    def scale_cluster(self, cluster, node_group_id_map):
        return _scale_cluster(cluster, node_group_id_map)

    def shutdown_cluster(self, cluster):
        _shutdown_cluster(cluster)

    def get_instances(self, cluster, instances_ids=None):
        return _get_instances(cluster, instances_ids)

    def clean_cluster_from_empty_ng(self, cluster):
        _clean_cluster_from_empty_ng(cluster)

    def get_node_group_image_username(self, node_group):
        return CLOUD_INIT_USERNAME


def _create_cluster(cluster):
    ctx = context.ctx()

    launcher = _CreateLauncher()

    try:
        target_count = _get_ng_counts(cluster)
        _nullify_ng_counts(cluster)

        cluster = conductor.cluster_get(ctx, cluster)

        launcher.launch_instances(ctx, cluster, target_count)
    except Exception as ex:
        LOG.warn("Can't start cluster '%s' (reason: %s)", cluster.name, ex)
        with excutils.save_and_reraise_exception():
            cluster = conductor.cluster_update(ctx, cluster,
                                               {"status": "Error",
                                                "status_description": str(ex)})
            LOG.info(g.format_cluster_status(cluster))
            _rollback_cluster_creation(cluster)


def _get_ng_counts(cluster):
    count = {}
    for node_group in cluster.node_groups:
        count[node_group.id] = node_group.count
    return count


def _nullify_ng_counts(cluster):
    ctx = context.ctx()

    for node_group in cluster.node_groups:
        conductor.node_group_update(ctx, node_group, {"count": 0})


def _get_instances(cluster, instances_ids=None):
    inst_map = {}
    for node_group in cluster.node_groups:
        for instance in node_group.instances:
            inst_map[instance.id] = instance

    if instances_ids is not None:
        return [inst_map[id] for id in instances_ids]
    else:
        return [v for v in six.itervalues(inst_map)]


def _scale_cluster(cluster, target_count):
    ctx = context.ctx()

    rollback_count = _get_ng_counts(cluster)

    launcher = _ScaleLauncher()

    try:
        launcher.launch_instances(ctx, cluster, target_count)
    except Exception as ex:
        LOG.warn("Can't scale cluster '%s' (reason: %s)", cluster.name, ex)
        with excutils.save_and_reraise_exception():
            cluster = conductor.cluster_get(ctx, cluster)

            try:
                _rollback_cluster_scaling(ctx, cluster, rollback_count,
                                          target_count)
            except Exception:
                # if something fails during the rollback, we stop
                # doing anything further
                cluster = conductor.cluster_update(ctx, cluster,
                                                   {"status": "Error"})
                LOG.info(g.format_cluster_status(cluster))
                LOG.error("Unable to complete rollback, aborting")
                raise

            cluster = conductor.cluster_update(ctx, cluster,
                                               {"status": "Active"})
            LOG.info(g.format_cluster_status(cluster))
            LOG.warn("Rollback successful. Throwing off an initial exception.")
    finally:
        cluster = conductor.cluster_get(ctx, cluster)
        _clean_cluster_from_empty_ng(cluster)

    return launcher.inst_ids


class _CreateLauncher(object):
    STAGES = ["Spawning", "Waiting", "Preparing"]
    UPDATE_STACK = False
    inst_ids = []

    def launch_instances(self, ctx, cluster, target_count):
        # create all instances
        cluster = conductor.cluster_update(ctx, cluster,
                                           {"status": self.STAGES[0]})
        LOG.info(g.format_cluster_status(cluster))

        tmpl = heat.ClusterTemplate(cluster.name,
                                    cluster.neutron_management_network,
                                    cluster.user_keypair_id)

        _configure_template(ctx, tmpl, cluster, target_count)
        stack = tmpl.instantiate(update_existing=self.UPDATE_STACK)
        stack.wait_till_active()

        self.inst_ids = _populate_cluster(ctx, cluster, stack)

        # wait for all instances are up and networks ready
        cluster = conductor.cluster_update(ctx, cluster,
                                           {"status": self.STAGES[1]})
        LOG.info(g.format_cluster_status(cluster))

        instances = _get_instances(cluster, self.inst_ids)

        _await_networks(cluster, instances)

        # prepare all instances
        cluster = conductor.cluster_update(ctx, cluster,
                                           {"status": self.STAGES[2]})
        LOG.info(g.format_cluster_status(cluster))

        instances = _get_instances(cluster, self.inst_ids)
        volumes.mount_to_instances(instances)

        _configure_instances(cluster)


class _ScaleLauncher(_CreateLauncher):
    STAGES = ["Scaling: Spawning", "Scaling: Waiting", "Scaling: Preparing"]
    UPDATE_STACK = True


class _RollbackLauncher(_CreateLauncher):
    STAGES = ["Rollback: Spawning", "Rollback: Waiting", "Rollback: Preparing"]
    UPDATE_STACK = True


def _generate_anti_affinity_groups(cluster):
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


def _configure_template(ctx, tmpl, cluster, target_count):
    for node_group in cluster.node_groups:
        userdata = _generate_user_data_script(node_group)
        count = target_count[node_group.id]
        tmpl.add_node_group(node_group.name, count,
                            node_group.flavor_id, node_group.get_image_id(),
                            userdata, node_group.floating_ip_pool,
                            node_group.volumes_per_node,
                            node_group.volumes_size,)

        # if number of instances decreases, we need to drop the excessive ones
        for i in range(count, node_group.count):
            conductor.instance_remove(ctx, node_group.instances[i])


def _populate_cluster(ctx, cluster, stack):
    old_ids = [i.instance_id for i in _get_instances(cluster)]

    new_ids = []

    for node_group in cluster.node_groups:
        nova_ids = stack.get_node_group_instances(node_group.name)
        for name, nova_id in nova_ids:
            if nova_id not in old_ids:
                instance_id = conductor.instance_add(ctx, node_group,
                                                     {"instance_id": nova_id,
                                                      "instance_name": name})
                new_ids.append(instance_id)

    return new_ids


def _generate_user_data_script(node_group):
    script_template = """#!/bin/bash
echo "%(public_key)s" >> %(user_home)s/.ssh/authorized_keys
echo "%(private_key)s" > %(user_home)s/.ssh/id_rsa
"""
    cluster = node_group.cluster

    user_home = "/home/%s" % CLOUD_INIT_USERNAME

    return script_template % {
        "public_key": cluster.management_public_key,
        "private_key": cluster.management_private_key,
        "user_home": user_home
    }


def _await_networks(cluster, instances):
    if not instances:
        return

    ips_assigned = set()
    while len(ips_assigned) != len(instances):
        if not g.check_cluster_exists(instances[0].node_group.cluster):
            return
        for instance in instances:
            if instance.id not in ips_assigned:
                if networks.init_instances_ips(instance):
                    ips_assigned.add(instance.id)

        context.sleep(1)

    LOG.info("Cluster '%s': all instances have IPs assigned" % cluster.id)

    ctx = context.ctx()
    cluster = conductor.cluster_get(ctx, instances[0].node_group.cluster)
    instances = _get_instances(cluster, ips_assigned)

    with context.ThreadGroup() as tg:
        for instance in instances:
            tg.spawn("wait-for-ssh-%s" % instance.instance_name,
                     _wait_until_accessible, instance)

    LOG.info("Cluster '%s': all instances are accessible" % cluster.id)


def _wait_until_accessible(instance):
    while True:
        try:
            # check if ssh is accessible and cloud-init
            # script is finished generating id_rsa
            exit_code, stdout = instance.remote().execute_command(
                "ls .ssh/id_rsa", raise_when_error=False)

            if exit_code == 0:
                LOG.debug('Instance %s is accessible' % instance.instance_name)
                return
        except Exception as ex:
            LOG.debug("Can't login to node %s (%s), reason %s",
                      instance.instance_name, instance.management_ip, ex)

        context.sleep(5)

        if not g.check_cluster_exists(instance.node_group.cluster):
            return


def _configure_instances(cluster):
    """Configure active instances.

    * generate /etc/hosts
    * setup passwordless login
    * etc.
    """
    hosts_file = _generate_etc_hosts(cluster)

    with context.ThreadGroup() as tg:
        for node_group in cluster.node_groups:
            for instance in node_group.instances:
                tg.spawn("configure-instance-%s" % instance.instance_name,
                         _configure_instance, instance, hosts_file)


def _configure_instance(instance, hosts_file):
    LOG.debug('Configuring instance %s' % instance.instance_name)

    with instance.remote() as r:
        r.write_file_to('etc-hosts', hosts_file)
        r.execute_command('sudo hostname %s' % instance.fqdn())
        r.execute_command('sudo mv etc-hosts /etc/hosts')

        r.execute_command('sudo usermod -s /bin/bash $USER')

        r.execute_command('sudo chown $USER:$USER .ssh/id_rsa')
        r.execute_command('chmod 400 .ssh/id_rsa')


def _generate_etc_hosts(cluster):
    hosts = "127.0.0.1 localhost\n"
    for node_group in cluster.node_groups:
        for instance in node_group.instances:
            hosts += "%s %s %s\n" % (instance.internal_ip,
                                     instance.fqdn(),
                                     instance.hostname())

    return hosts


def _rollback_cluster_creation(cluster):
    """Shutdown all instances and update cluster status."""
    LOG.info("Cluster '%s' creation rollback", cluster.name)

    _shutdown_cluster(cluster)


def _rollback_cluster_scaling(ctx, cluster, rollback_count, target_count):
    """Attempt to rollback cluster scaling.

    Our rollback policy for scaling is as follows:
    We shut down nodes created during scaling, but we don't try to
    to get back decommissioned nodes. I.e. during the rollback
    we only shut down nodes and not launch them. That approach should
    maximize the change of rollback success.
    """

    LOG.info("Cluster '%s' scaling rollback", cluster.name)

    for ng in rollback_count.keys():
        if rollback_count[ng] > target_count[ng]:
            rollback_count[ng] = target_count[ng]

    launcher = _RollbackLauncher()
    launcher.launch_instances(ctx, cluster, rollback_count)


def _clean_job_executions(cluster):
    ctx = context.ctx()
    for je in conductor.job_execution_get_all(ctx, cluster_id=cluster.id):
        update = {"cluster_id": None,
                  "end_time": datetime.datetime.now()}
        conductor.job_execution_update(ctx, je, update)


def _shutdown_cluster(cluster):
    """Shutdown specified cluster and all related resources."""
    try:
        heat.client().stacks.delete(cluster.name)
    except heat_exc.HTTPNotFound:
        LOG.warn('Did not found stack for cluster %s' % cluster.name)

    _clean_job_executions(cluster)

    ctx = context.ctx()
    instances = _get_instances(cluster)
    for inst in instances:
        conductor.instance_remove(ctx, inst)


def _clean_cluster_from_empty_ng(cluster):
    ctx = context.ctx()
    for ng in cluster.node_groups:
        if ng.count == 0:
            conductor.node_group_remove(ctx, ng)
