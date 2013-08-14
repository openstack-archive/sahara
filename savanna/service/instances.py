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

from savanna import context
from savanna.db import models as m
from savanna.openstack.common import excutils
from savanna.openstack.common import log as logging
from savanna.service import networks
from savanna.service import volumes
from savanna.utils import crypto
from savanna.utils import general as g
from savanna.utils.openstack import nova

LOG = logging.getLogger(__name__)


def create_cluster(cluster):
    try:
        # create all instances
        context.model_update(cluster, status='Spawning')
        LOG.info(g.format_cluster_status(cluster))
        _create_instances(cluster)

        # wait for all instances are up and accessible
        context.model_update(cluster, status='Waiting')
        LOG.info(g.format_cluster_status(cluster))
        _await_instances(cluster)

        # attach volumes
        volumes.attach(cluster)

        # prepare all instances
        context.model_update(cluster, status='Preparing')
        LOG.info(g.format_cluster_status(cluster))
        _configure_instances(cluster)
    except Exception as ex:
        LOG.warn("Can't start cluster '%s' (reason: %s)", cluster.name, ex)
        with excutils.save_and_reraise_exception():
            context.model_update(cluster, status='Error',
                                 status_description=str(ex))
            LOG.info(g.format_cluster_status(cluster))
            _rollback_cluster_creation(cluster, ex)


def scale_cluster(cluster, node_group_names_map, plugin):
    # Now let's work with real node_groups, not names:
    node_groups_map = {}
    for ng in cluster.node_groups:
        if ng.name in node_group_names_map:
            node_groups_map.update({ng: node_group_names_map[ng.name]})
    instances_list = []
    try:
        instances_list = _scale_cluster_instances(
            cluster, node_groups_map, plugin)
        _clean_cluster_from_empty_ng(cluster)
        _await_instances(cluster)
        volumes.attach_to_instances(instances_list)

    except Exception as ex:
        LOG.warn("Can't scale cluster '%s' (reason: %s)", cluster.name, ex)
        with excutils.save_and_reraise_exception():
            _rollback_cluster_scaling(cluster, instances_list, ex)
            instances_list = []
            _clean_cluster_from_empty_ng(cluster)
            if cluster.status == 'Decommissioning':
                context.model_update(cluster, status='Error')
            else:
                context.model_update(cluster, status='Active')
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
    aa_groups = _generate_anti_affinity_groups(cluster)
    for node_group in cluster.node_groups:
        userdata = _generate_user_data_script(node_group)
        for idx in xrange(1, node_group.count + 1):
            _run_instance(cluster, node_group, idx, aa_groups, userdata)


def _scale_cluster_instances(cluster, node_groups_map, plugin):
    aa_groups = _generate_anti_affinity_groups(cluster)
    instances_to_delete = []
    node_groups_to_enlarge = []

    for node_group in node_groups_map:
        count = node_groups_map[node_group]
        if count < node_group.count:
            instances_to_delete += node_group.instances[count:node_group.count]
        else:
            node_groups_to_enlarge.append(node_group)

    if instances_to_delete:
        cluster.status = 'Decommissioning'
        LOG.info(g.format_cluster_status(cluster))
        plugin.decommission_nodes(cluster, instances_to_delete)
        cluster.status = 'Deleting Instances'
        LOG.info(g.format_cluster_status(cluster))
        for instance in instances_to_delete:
            node_group = instance.node_group
            node_group.instances.remove(instance)
            _shutdown_instance(instance)
            node_group.count -= 1
            context.model_save(node_group)

    instances_to_add = []
    if node_groups_to_enlarge:
        cluster.status = 'Adding Instances'
        LOG.info(g.format_cluster_status(cluster))
        for node_group in node_groups_to_enlarge:
            count = node_groups_map[node_group]
            userdata = _generate_user_data_script(node_group)
            for idx in xrange(node_group.count + 1, count + 1):
                instance = _run_instance(cluster, node_group, idx,
                                         aa_groups, userdata)
                instances_to_add.append(instance)
            node_group.count = count

    return instances_to_add


def _run_instance(cluster, node_group, idx, aa_groups, userdata):
    """Create instance using nova client and persist them into DB."""
    session = context.ctx().session
    name = '%s-%s-%03d' % (cluster.name, node_group.name, idx)

    # aa_groups: node process -> instance ids
    aa_ids = []
    for node_process in node_group.node_processes:
        aa_ids += aa_groups.get(node_process) or []

    # create instances only at hosts w/ no instances w/ aa-enabled processes
    hints = {'different_host': list(set(aa_ids))} if aa_ids else None

    context.model_save(node_group)

    nova_instance = nova.client().servers.create(
        name, node_group.get_image_id(), node_group.flavor_id,
        scheduler_hints=hints, userdata=userdata,
        key_name=cluster.user_keypair_id)

    with session.begin():
        instance = m.Instance(node_group.id, nova_instance.id, name)
        node_group.instances.append(instance)
        session.add(instance)

    # save instance id to aa_groups to support aa feature
    for node_process in node_group.node_processes:
        if node_process in cluster.anti_affinity:
            aa_group_ids = aa_groups.get(node_process, [])
            aa_group_ids.append(nova_instance.id)
            aa_groups[node_process] = aa_group_ids

    return instance


def _generate_user_data_script(node_group):
    script_template = """#!/bin/bash
echo "%(public_key)s" >> %(user_home)s/.ssh/authorized_keys
echo "%(private_key)s" > %(user_home)s/.ssh/id_rsa
"""
    cluster = node_group.cluster
    if node_group.username == "root":
        user_home = "/root/"
    else:
        user_home = "/home/%s/" % node_group.username

    return script_template % {
        "public_key": crypto.private_key_to_public_key(cluster.private_key),
        "private_key": cluster.private_key,
        "user_home": user_home
    }


def _await_instances(cluster):
    """Await all instances are in Active status and available."""
    all_up = False
    while not all_up:
        all_up = True
        for node_group in cluster.node_groups:
            for instance in node_group.instances:
                if not _check_if_up(instance):
                    all_up = False
        context.sleep(1)


def _check_if_up(instance):
    if hasattr(instance, '_is_up'):
        return True

    server = instance.nova_info
    if server.status == 'ERROR':
        # TODO(slukjanov): replace with specific error
        raise RuntimeError("node %s has error status" % server.name)

    if server.status != 'ACTIVE':
        return False

    if len(server.networks) == 0:
        return False

    if not networks.init_instances_ips(instance, server):
        return False

    try:
        exit_code, _ = instance.remote.execute_command("hostname")
        if exit_code:
            return False
    except Exception as ex:
        LOG.debug("Can't login to node %s (%s), reason %s",
                  server.name, instance.management_ip, ex)
        return False

    instance._is_up = True
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
            with instance.remote as remote:
                remote.write_file_to('etc-hosts', hosts)
                remote.execute_command('sudo mv etc-hosts /etc/hosts')
                remote.execute_command('chmod 400 .ssh/id_rsa')


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

    session = context.ctx().session
    _shutdown_instances(cluster, True)
    volumes.detach(cluster)
    alive_instances = set([srv.id for srv in nova.client().servers.list()])

    for node_group in cluster.node_groups:
        for instance in node_group.instances:
            if instance.instance_id in alive_instances:
                nova.client().servers.delete(instance.instance_id)
            with session.begin():
                session.delete(instance)


def _rollback_cluster_scaling(cluster, instances, ex):
    """Attempt to rollback cluster scaling."""
    LOG.info("Cluster '%s' scaling rollback (reason: %s)", cluster.name, ex)
    try:
        volumes.detach_from_instances(instances)
    except Exception:
        raise
    finally:
        for i in instances:
            ng = i.node_group
            _shutdown_instance(i)
            ng.count -= 1


def _shutdown_instances(cluster, quiet=False):
    for node_group in cluster.node_groups:
        for instance in node_group.instances:
            _shutdown_instance(instance)


def _shutdown_instance(instance):
    session = context.ctx().session
    try:
        nova.client().servers.delete(instance.instance_id)
    except nova_exceptions.NotFound:
        #Just ignore non-existing instances
        pass

    with session.begin():
        session.delete(instance)


def shutdown_cluster(cluster):
    """Shutdown specified cluster and all related resources."""
    volumes.detach(cluster)
    _shutdown_instances(cluster)


def _clean_cluster_from_empty_ng(cluster):
    session = context.ctx().session
    with session.begin():
        all_ng = cluster.node_groups
    for ng in all_ng:
        if ng.count == 0:
            session.delete(ng)
            cluster.node_groups.remove(ng)
