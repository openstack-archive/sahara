# Copyright (c) 2014, MapR Technologies
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from sahara.plugins.mapr.util import names
import sahara.plugins.utils as u


ZOOKEEPER_CLIENT_PORT = 5181


def get_cldb_nodes_ip(cluster):
    cldb_node_list = u.get_instances(cluster, names.CLDB)
    return ','.join([i.management_ip for i in cldb_node_list])


def get_zookeeper_nodes_ip(cluster):
    zkeeper_node_list = u.get_instances(cluster, names.ZOOKEEPER)
    return ','.join([i.management_ip for i in zkeeper_node_list])


def get_zookeeper_nodes_ip_with_port(cluster):
    zkeeper_node_list = u.get_instances(cluster, names.ZOOKEEPER)
    return ','.join(['%s:%s' % (i.management_ip, ZOOKEEPER_CLIENT_PORT)
                     for i in zkeeper_node_list])


def get_resourcemanager_ip(cluster):
    rm_instance = u.get_instance(cluster, names.RESOURCE_MANAGER)
    return rm_instance.management_ip


def get_historyserver_ip(cluster):
    hs_instance = u.get_instance(cluster, names.HISTORY_SERVER)
    return hs_instance.management_ip


def get_jobtracker(cluster):
    instance = u.get_instance(cluster, names.JOBTRACKER)
    return instance


def get_resourcemanager(cluster):
    return u.get_instance(cluster, names.RESOURCE_MANAGER)


def get_nodemanagers(cluster):
    return u.get_instances(cluster, names.NODE_MANAGER)


def get_oozie(cluster):
    return u.get_instance(cluster, names.OOZIE)


def get_datanodes(cluster):
    return u.get_instances(cluster, names.DATANODE)


def get_tasktrackers(cluster):
    return u.get_instances(cluster, names.TASK_TRACKER)


def get_secondarynamenodes(cluster):
    return u.get_instances(cluster, names.SECONDARY_NAMENODE)


def get_historyserver(cluster):
    return u.get_instance(cluster, names.HISTORY_SERVER)
