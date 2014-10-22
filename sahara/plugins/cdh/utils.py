# Copyright (c) 2014 Mirantis Inc.
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

from sahara.plugins import utils as u


def get_manager(cluster):
    return u.get_instance(cluster, 'MANAGER')


def get_namenode(cluster):
    return u.get_instance(cluster, "NAMENODE")


def get_resourcemanager(cluster):
    return u.get_instance(cluster, 'RESOURCEMANAGER')


def get_nodemanagers(cluster):
    return u.get_instances(cluster, 'NODEMANAGER')


def get_oozie(cluster):
    return u.get_instance(cluster, 'OOZIE_SERVER')


def get_datanodes(cluster):
    return u.get_instances(cluster, 'DATANODE')


def get_secondarynamenode(cluster):
    return u.get_instance(cluster, 'SECONDARYNAMENODE')


def get_historyserver(cluster):
    return u.get_instance(cluster, 'JOBHISTORY')


def get_hive_metastore(cluster):
    return u.get_instance(cluster, 'HIVEMETASTORE')


def get_hue(cluster):
    return u.get_instance(cluster, 'HUE_SERVER')


def get_spark_historyserver(cluster):
    return u.get_instance(cluster, 'SPARK_YARN_HISTORY_SERVER')
