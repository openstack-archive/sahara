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

from savanna import conductor as c
from savanna import context
from savanna.openstack.common import excutils
from savanna.openstack.common import log as logging
from savanna.service import networks
from savanna.service import volumes
from savanna.utils import general as g
from savanna.utils.openstack import nova


conductor = c.API
CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def create_cluster(cluster):
    ctx = context.ctx()
    try:
        # create all instances
        conductor.cluster_update(ctx, cluster, {"status": "Spawning"})
        LOG.info(g.format_cluster_status(cluster))
        _create_instances(cluster)

        # wait for all instances are up and accessible
        cluster = conductor.cluster_update(ctx, cluster, {"status": "Waiting"})
        LOG.info(g.format_cluster_status(cluster))
        cluster = _await_instances(cluster)

        # attach volumes
        volumes.attach(cluster)

        # prepare all instances
        cluster = conductor.cluster_update(ctx, cluster,
                                           {"status": "Preparing"})
        LOG.info(g.format_cluster_status(cluster))

        _configure_instances(cluster)
    except Exception as ex:
        LOG.warn("Can't start cluster '%s' (reason: %s)", cluster.name, ex)
        with excutils.save_and_reraise_exception():
            cluster = conductor.cluster_update(ctx, cluster,
                                               {"status": "Error",
                                                "status_description": str(ex)})
            LOG.info(g.format_cluster_status(cluster))
            _rollback_cluster_creation(cluster, ex)


def get_instances(cluster, instances_ids):
    inst_map = {}
    for node_group in cluster.node_groups:
        for instance in node_group.instances:
            inst_map[instance.id] = instance

    return [inst_map[id] for id in instances_ids]


def scale_cluster(cluster, node_group_id_map, plugin):
    ctx = context.ctx()

    instances_list = []
    try:
        instances_list = _scale_cluster_instances(
            cluster, node_group_id_map, plugin)

        cluster = conductor.cluster_get(ctx, cluster)
        cluster = clean_cluster_from_empty_ng(cluster)

        cluster = _await_instances(cluster)

        volumes.attach_to_instances(get_instances(cluster, instances_list))

    except Exception as ex:
        LOG.warn("Can't scale cluster '%s' (reason: %s)", cluster.name, ex)
        with excutils.save_and_reraise_exception():
            cluster = conductor.cluster_get(ctx, cluster)
            _rollback_cluster_scaling(cluster,
                                      get_instances(cluster, instances_list),
                                      ex)
            instances_list = []

            cluster = conductor.cluster_get(ctx, cluster)
            clean_cluster_from_empty_ng(cluster)
            if cluster.status == 'Decommissioning':
                cluster = conductor.cluster_update(ctx, cluster,
                                                   {"status": "Error"})
            else:
                cluster = conductor.cluster_update(ctx, cluster,
                                                   {"status": "Active"})

            LOG.info(g.format_cluster_status(cluster))

    # we should be here with valid cluster: if instances creation
    # was not successful all extra-instances will be removed above
    if instances_list:
        _configure_instances(cluster)
    return instances_list


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


def _create_instances(cluster):
    ctx = context.ctx()

    #aa_groups = _generate_anti_affinity_groups(cluster)
    aa_groups = {}

    for node_group in cluster.node_groups:
        count = node_group.count
        conductor.node_group_update(ctx, node_group, {'count': 0})
        userdata = _generate_user_data_script(node_group)
        for idx in xrange(1, count + 1):
            _run_instance(cluster, node_group, idx, aa_groups, userdata)


def _scale_cluster_instances(cluster, node_group_id_map, plugin):
    ctx = context.ctx()
    aa_groups = _generate_anti_affinity_groups(cluster)
    instances_to_delete = []
    node_groups_to_enlarge = []

    for node_group in cluster.node_groups:
        if node_group.id not in node_group_id_map:
            continue

        new_count = node_group_id_map[node_group.id]
        if new_count < node_group.count:
            instances_to_delete += node_group.instances[new_count:
                                                        node_group.count]
        else:
            node_groups_to_enlarge.append(node_group)

    if instances_to_delete:
        conductor.cluster_update(ctx, cluster, {"status": "Decommissioning"})
        LOG.info(g.format_cluster_status(cluster))
        plugin.decommission_nodes(cluster, instances_to_delete)
        cluster = conductor.cluster_update(ctx, cluster,
                                           {"status": "Deleting Instances"})
        LOG.info(g.format_cluster_status(cluster))
        for instance in instances_to_delete:
            _shutdown_instance(instance)

    cluster = conductor.cluster_get(ctx, cluster)

    instances_to_add = []
    if node_groups_to_enlarge:
        cluster = conductor.cluster_update(ctx, cluster,
                                           {"status": "Adding Instances"})
        LOG.info(g.format_cluster_status(cluster))
        for node_group in node_groups_to_enlarge:
            count = node_group_id_map[node_group.id]
            userdata = _generate_user_data_script(node_group)
            for idx in xrange(node_group.count + 1, count + 1):
                instance_id = _run_instance(cluster, node_group, idx,
                                            aa_groups, userdata)
                instances_to_add.append(instance_id)

    return instances_to_add


def _find_by_id(lst, id):
    for obj in lst:
        if obj.id == id:
            return obj

    return None


def _run_instance(cluster, node_group, idx, aa_groups, userdata):
    """Create instance using nova client and persist them into DB."""
    ctx = context.ctx()
    name = '%s-%s-%03d' % (cluster.name, node_group.name, idx)

    # aa_groups: node process -> instance ids
    aa_ids = []
    for node_process in node_group.node_processes:
        aa_ids += aa_groups.get(node_process) or []

    # create instances only at hosts w/ no instances w/ aa-enabled processes
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


def _generate_user_data_script(node_group):
    script_template = """#!/bin/bash
echo "%(public_key)s" >> %(user_home)s/.ssh/authorized_keys
echo "%(private_key)s" > %(user_home)s/.ssh/id_rsa
"""
    cluster = node_group.cluster
    if nova.get_node_group_image_username(node_group) == "root":
        user_home = "/root/"
    else:
        user_home = "/home/%s/" % nova.get_node_group_image_username(
            node_group)

    return script_template % {
        "public_key": cluster.management_public_key,
        "private_key": cluster.management_private_key,
        "user_home": user_home
    }


def _await_instances(cluster):
    """Await all instances are in Active status and available."""
    ctx = context.ctx()
    all_up = False
    is_accesible = set()
    while not all_up:
        all_up = True

        for node_group in cluster.node_groups:
            for instance in node_group.instances:
                if not _check_if_up(instance):
                    all_up = False

        cluster = conductor.cluster_get(ctx, cluster)

        for node_group in cluster.node_groups:
            for instance in node_group.instances:
                if not _check_if_accessible(instance, is_accesible):
                    all_up = False

        context.sleep(1)

    return cluster


def _check_if_up(instance):
    if instance.internal_ip and instance.management_ip:
        return True

    server = nova.get_instance_info(instance)
    if server.status == 'ERROR':
        # TODO(slukjanov): replace with specific error
        raise RuntimeError("node %s has error status" % server.name)

    if server.status != 'ACTIVE':
        return False

    if len(server.networks) == 0:
        return False

    if not networks.init_instances_ips(instance, server):
        return False

    return True


def _check_if_accessible(instance, cache):
    if instance.id in cache:
        return True

    if not instance.internal_ip or not instance.management_ip:
        # instance is not up yet
        return False

    try:
        # check if ssh is accessible and cloud-init
        # script is finished generating id_rsa
        exit_code, _ = instance.remote.execute_command(
            "ls .ssh/id_rsa", raise_when_error=False)
        # don't log ls command failure
        if exit_code:
            return False
    except Exception as ex:
        LOG.debug("Can't login to node %s (%s), reason %s",
                  instance.instance_name, instance.management_ip, ex)
        return False

    LOG.debug('Instance %s is accessible' % instance.instance_name)
    cache.add(instance.id)
    return True


def _configure_instances(cluster):
    """Configure active instances.

    * generate /etc/hosts
    * setup passwordless login
    * etc.
    """
    hosts = _generate_etc_hosts(cluster)
    for node_group in cluster.node_groups:
        for instance in node_group.instances:
            LOG.debug('Configuring instance %s' % instance.instance_name)
            with instance.remote as r:
                r.write_file_to('etc-hosts', hosts)
                r.execute_command('sudo mv etc-hosts /etc/hosts')

                r.execute_command('sudo chown $USER:$USER .ssh/id_rsa')
                r.execute_command('chmod 400 .ssh/id_rsa')


def _generate_etc_hosts(cluster):
    hosts = "127.0.0.1 localhost\n"
    for node_group in cluster.node_groups:
        for instance in node_group.instances:
            hosts += "%s %s %s\n" % (instance.internal_ip,
                                     instance.fqdn,
                                     instance.hostname)

    return hosts


def _rollback_cluster_creation(cluster, ex):
    """Shutdown all instances and update cluster status."""
    LOG.info("Cluster '%s' creation rollback (reason: %s)", cluster.name, ex)

    shutdown_cluster(cluster)


def _rollback_cluster_scaling(cluster, instances, ex):
    """Attempt to rollback cluster scaling."""
    LOG.info("Cluster '%s' scaling rollback (reason: %s)", cluster.name, ex)
    try:
        volumes.detach_from_instances(instances)
    finally:
        for i in instances:
            _shutdown_instance(i)


def _clean_job_executions(cluster):
    ctx = context.ctx()
    for je in conductor.job_execution_get_by_cluster(ctx, cluster.id):
        conductor.job_execution_update(ctx, je, {"cluster_id": None})


def _shutdown_instances(cluster):
    for node_group in cluster.node_groups:
        for instance in node_group.instances:
            _shutdown_instance(instance)


def _shutdown_instance(instance):
    ctx = context.ctx()
    try:
        nova.client().servers.delete(instance.instance_id)
    except nova_exceptions.NotFound:
        #Just ignore non-existing instances
        pass

    conductor.instance_remove(ctx, instance)


def shutdown_cluster(cluster):
    """Shutdown specified cluster and all related resources."""
    try:
        volumes.detach(cluster)
    finally:
        _shutdown_instances(cluster)
        _clean_job_executions(cluster)


def clean_cluster_from_empty_ng(cluster):
    ctx = context.ctx()
    for ng in cluster.node_groups:
        if ng.count == 0:
            conductor.node_group_remove(ctx, ng)

    return conductor.cluster_get(ctx, cluster)
