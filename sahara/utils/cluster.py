# Copyright (c) 2015 Intel Inc.
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

import socket

from keystoneauth1 import exceptions as keystone_ex
from oslo_config import cfg
from oslo_log import log as logging
from six.moves.urllib import parse

from sahara import conductor as c
from sahara import context
from sahara import exceptions as e
from sahara.utils.notification import sender
from sahara.utils.openstack import base as auth_base

conductor = c.API
LOG = logging.getLogger(__name__)

CONF = cfg.CONF

# cluster status
CLUSTER_STATUS_VALIDATING = "Validating"
CLUSTER_STATUS_INFRAUPDATING = "InfraUpdating"
CLUSTER_STATUS_SPAWNING = "Spawning"
CLUSTER_STATUS_WAITING = "Waiting"
CLUSTER_STATUS_PREPARING = "Preparing"
CLUSTER_STATUS_CONFIGURING = "Configuring"
CLUSTER_STATUS_STARTING = "Starting"
CLUSTER_STATUS_ACTIVE = "Active"
CLUSTER_STATUS_DECOMMISSIONING = "Decommissioning"
CLUSTER_STATUS_ERROR = "Error"
CLUSTER_STATUS_DELETING = "Deleting"
CLUSTER_STATUS_AWAITINGTERMINATION = "AwaitingTermination"

# cluster status -- Instances
CLUSTER_STATUS_DELETING_INSTANCES = "Deleting Instances"
CLUSTER_STATUS_ADDING_INSTANCES = "Adding Instances"

# Scaling status
CLUSTER_STATUS_SCALING = "Scaling"
CLUSTER_STATUS_SCALING_SPAWNING = (CLUSTER_STATUS_SCALING +
                                   ": " + CLUSTER_STATUS_SPAWNING)
CLUSTER_STATUS_SCALING_WAITING = (CLUSTER_STATUS_SCALING +
                                  ": " + CLUSTER_STATUS_WAITING)
CLUSTER_STATUS_SCALING_PREPARING = (CLUSTER_STATUS_SCALING +
                                    ": " + CLUSTER_STATUS_PREPARING)

# Rollback status
CLUSTER_STATUS_ROLLBACK = "Rollback"
CLUSTER_STATUS_ROLLBACK_SPAWNING = (CLUSTER_STATUS_ROLLBACK +
                                    ": " + CLUSTER_STATUS_SPAWNING)
CLUSTER_STATUS_ROLLBACK_WAITING = (CLUSTER_STATUS_ROLLBACK +
                                   ": " + CLUSTER_STATUS_WAITING)
CLUSTER_STATUS_ROLLBACK__PREPARING = (CLUSTER_STATUS_ROLLBACK +
                                      ": " + CLUSTER_STATUS_PREPARING)


def change_cluster_status_description(cluster, status_description):
    try:
        ctx = context.ctx()
        return conductor.cluster_update(
            ctx, cluster, {'status_description': status_description})
    except e.NotFoundException:
        return None


def change_cluster_status(cluster, status, status_description=None):
    ctx = context.ctx()

    # Update cluster status. Race conditions with deletion are still possible,
    # but this reduces probability at least.
    cluster = conductor.cluster_get(ctx, cluster) if cluster else None

    if status_description is not None:
        change_cluster_status_description(cluster, status_description)

    # 'Deleting' is final and can't be changed
    if cluster is None or cluster.status == CLUSTER_STATUS_DELETING:
        return cluster

    update_dict = {"status": status}
    cluster = conductor.cluster_update(ctx, cluster, update_dict)
    conductor.cluster_provision_progress_update(ctx, cluster.id)

    LOG.info("Cluster status has been changed. New status="
             "{status}".format(status=cluster.status))

    sender.status_notify(cluster.id, cluster.name, cluster.status,
                         "update")

    return cluster


def count_instances(cluster):
    return sum([node_group.count for node_group in cluster.node_groups])


def check_cluster_exists(cluster):
    ctx = context.ctx()
    # check if cluster still exists (it might have been removed)
    cluster = conductor.cluster_get(ctx, cluster)
    return cluster is not None


def get_instances(cluster, instances_ids=None):
    inst_map = {}
    for node_group in cluster.node_groups:
        for instance in node_group.instances:
            inst_map[instance.id] = instance

    if instances_ids is not None:
        return [inst_map[id] for id in instances_ids]
    else:
        return [v for v in inst_map.values()]


def clean_cluster_from_empty_ng(cluster):
    ctx = context.ctx()
    for ng in cluster.node_groups:
        if ng.count == 0:
            conductor.node_group_remove(ctx, ng)


def etc_hosts_entry_for_service(service):
    result = ""
    try:
        hostname = parse.urlparse(
            auth_base.url_for(service_type=service,
                              endpoint_type="publicURL")).hostname
    except keystone_ex.EndpointNotFound:
        LOG.debug("Endpoint not found for service: '{}'".format(service))
        return result

    overridden_ip = (
        getattr(CONF, "%s_ip_accessible" % service.replace('-', '_'), None)
    )
    if overridden_ip is not None:
        return "%s %s\n" % (overridden_ip, hostname)

    try:
        result = "%s %s\n" % (socket.gethostbyname(hostname), hostname)
    except socket.gaierror:
        LOG.warning("Failed to resolve hostname of service: '{}'"
                    .format(service))
        result = "# Failed to resolve {} during deployment\n".format(hostname)
    return result


def _etc_hosts_for_services(hosts):
    # add alias for keystone and swift
    for service in ["identity", "object-store"]:
        hosts += etc_hosts_entry_for_service(service)
    return hosts


def _etc_hosts_for_instances(hosts, cluster):
    for node_group in cluster.node_groups:
        for instance in node_group.instances:
            hosts += "%s %s %s\n" % (instance.internal_ip,
                                     instance.fqdn(),
                                     instance.hostname())
    return hosts


def generate_etc_hosts(cluster):
    hosts = "127.0.0.1 localhost\n"
    if not cluster.use_designate_feature():
        hosts = _etc_hosts_for_instances(hosts, cluster)
    hosts = _etc_hosts_for_services(hosts)
    return hosts


def generate_resolv_conf_diff(curr_resolv_conf):
    # returns string that contains nameservers
    # which are lacked in the 'curr_resolve_conf'
    resolv_conf = ""
    for ns in CONF.nameservers:
        if ns not in curr_resolv_conf:
            resolv_conf += "nameserver {}\n".format(ns)
    return resolv_conf
