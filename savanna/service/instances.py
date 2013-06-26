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

from savanna import context
from savanna.db import models as m
from savanna.openstack.common import excutils
from savanna.openstack.common import log as logging
from savanna.service import networks
from savanna.utils import crypto
from savanna.utils.openstack import nova

LOG = logging.getLogger(__name__)


def create_cluster(cluster):
    try:
        # create all instances
        cluster.status = 'Spawning'
        context.model_save(cluster)
        _create_instances(cluster)

        # wait for all instances are up and accessible
        cluster.status = 'Waiting'
        context.model_save(cluster)
        _await_instances(cluster)

        # prepare all instances
        cluster.status = 'Preparing'
        context.model_save(cluster)
        _configure_instances(cluster)
    except Exception as ex:
        LOG.warn("Can't start cluster: %s", ex)
        with excutils.save_and_reraise_exception():
            _rollback_cluster_creation(cluster, ex)


def _create_instances(cluster):
    """Create all instances using nova client and persist them into DB."""
    session = context.ctx().session
    aa_groups = _generate_anti_affinity_groups(cluster)
    for node_group in cluster.node_groups:
        userdata = _generate_user_data_script(node_group)
        for idx in xrange(1, node_group.count + 1):
            name = '%s-%s-%03d' % (cluster.name, node_group.name, idx)
            aa_group = node_group.anti_affinity_group
            ids = aa_groups[aa_group]
            hints = {'different_host': list(ids)} if ids else None

            nova_instance = nova.client().servers.create(
                name, node_group.get_image_id(), node_group.flavor_id,
                scheduler_hints=hints, userdata=userdata,
                key_name=cluster.user_keypair_id)

            with session.begin():
                instance = m.Instance(node_group.id, nova_instance.id, name)
                node_group.instances.append(instance)
                session.add(instance)

            if aa_group:
                aa_groups[aa_group].append(nova_instance.id)


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


def _generate_anti_affinity_groups(cluster):
    return dict((ng.anti_affinity_group, []) for ng in cluster.node_groups)


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
    # update cluster status
    # update cluster status description
    _shutdown_instances(cluster, True)


def _shutdown_instances(cluster, quiet=False):
    """Shutdown all instances related to the specified cluster."""
    session = context.ctx().session

    for node_group in cluster.node_groups:
        for instance in node_group.instances:
            nova.client().servers.delete(instance.instance_id)
            with session.begin():
                session.delete(instance)


def shutdown_cluster(cluster):
    """Shutdown specified cluster and all related resources."""
    _shutdown_instances(cluster)
