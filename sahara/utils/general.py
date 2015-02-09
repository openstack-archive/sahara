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

import functools
import re

from oslo_log import log as logging
from oslo_utils import timeutils
import six

from sahara import conductor as c
from sahara import context
from sahara import exceptions as e
from sahara.i18n import _LI
from sahara.utils.notification import sender

conductor = c.API
LOG = logging.getLogger(__name__)

NATURAL_SORT_RE = re.compile('([0-9]+)')


def find_dict(iterable, **rules):
    """Search for dict in iterable of dicts using specified key-value rules."""

    for item in iterable:
        # assert all key-value pairs from rules dict
        ok = True
        for k, v in six.iteritems(rules):
            ok = ok and k in item and item[k] == v

        if ok:
            return item

    return None


def find(lst, **kwargs):
    for obj in lst:
        match = True
        for attr, value in kwargs.items():
            if getattr(obj, attr) != value:
                match = False

        if match:
            return obj

    return None


def get_by_id(lst, id):
    for obj in lst:
        if obj.id == id:
            return obj

    return None


# Taken from http://stackoverflow.com/questions/4836710/does-
# python-have-a-built-in-function-for-string-natural-sort
def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(NATURAL_SORT_RE, s)]


def change_cluster_status_description(cluster, status_description):
    ctx = context.ctx()

    cluster = conductor.cluster_get(ctx, cluster) if cluster else None

    if cluster is None or cluster.status == "Deleting":
        return cluster
    return conductor.cluster_update(
        ctx, cluster, {'status_description': status_description})


def change_cluster_status(cluster, status, status_description=None):
    ctx = context.ctx()

    # Update cluster status. Race conditions with deletion are still possible,
    # but this reduces probability at least.
    cluster = conductor.cluster_get(ctx, cluster) if cluster else None

    # 'Deleting' is final and can't be changed
    if cluster is None or cluster.status == 'Deleting':
        return cluster

    update_dict = {"status": status}
    if status_description:
        update_dict["status_description"] = status_description

    cluster = conductor.cluster_update(ctx, cluster, update_dict)

    LOG.info(_LI("Cluster status has been changed: id={id}, New status="
                 "{status}").format(id=cluster.id, status=cluster.status))

    sender.notify(ctx, cluster.id, cluster.name, cluster.status,
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
        return [v for v in six.itervalues(inst_map)]


def clean_cluster_from_empty_ng(cluster):
    ctx = context.ctx()
    for ng in cluster.node_groups:
        if ng.count == 0:
            conductor.node_group_remove(ctx, ng)


def generate_etc_hosts(cluster):
    hosts = "127.0.0.1 localhost\n"
    for node_group in cluster.node_groups:
        for instance in node_group.instances:
            hosts += "%s %s %s\n" % (instance.internal_ip,
                                     instance.fqdn(),
                                     instance.hostname())

    return hosts


def generate_instance_name(cluster_name, node_group_name, index):
    return ("%s-%s-%03d" % (cluster_name, node_group_name, index)).lower()


def generate_auto_security_group_name(node_group):
    return ("%s-%s-%s" % (node_group.cluster.name, node_group.name,
                          node_group.id[:8])).lower()


def generate_aa_group_name(cluster_name):
    return ("%s-aa-group" % cluster_name).lower()


def _get_consumed(start_time):
    return timeutils.delta_seconds(start_time, timeutils.utcnow())


def get_obj_in_args(check_obj, *args, **kwargs):
    for arg in args:
        val = check_obj(arg)
        if val is not None:
            return val

    for arg in kwargs.values():
        val = check_obj(arg)
        if val is not None:
            return val
    return None


def await_process(timeout, sleeping_time, op_name, check_object):
    """"Awaiting something in cluster."""
    def decorator(func):
        @functools.wraps(func)
        def handler(*args, **kwargs):
            start_time = timeutils.utcnow()
            cluster = get_obj_in_args(check_object, *args, **kwargs)

            while _get_consumed(start_time) < timeout:
                consumed = _get_consumed(start_time)
                if func(*args, **kwargs):
                    LOG.info(
                        _LI("Operation {op_name} was successfully executed "
                            "in seconds: {sec}").format(op_name=op_name,
                                                        sec=consumed))
                    return

                if not check_cluster_exists(cluster):
                    return

                context.sleep(sleeping_time)

            raise e.TimeoutException(timeout, op_name)
        return handler
    return decorator
