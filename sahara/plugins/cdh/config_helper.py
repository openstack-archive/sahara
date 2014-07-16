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

import json

from sahara.plugins import provisioning as p
from sahara.utils import files as f

DEFAULT_CDH5_UBUNTU_REPO_LIST_URL = ('http://archive.cloudera.com/cdh5/ubuntu'
                                     '/precise/amd64/cdh/cloudera.list')

DEFAULT_CDH5_UBUNTU_REPO_KEY_URL = ('http://archive.cloudera.com/cdh5/ubuntu'
                                    '/precise/amd64/cdh/archive.key')

DEFAULT_CM5_UBUNTU_REPO_LIST_URL = ('http://archive.cloudera.com/cm5/ubuntu'
                                    '/precise/amd64/cm/cloudera.list')

DEFAULT_CM5_UBUNTU_REPO_KEY_URL = ('http://archive.cloudera.com/cm5/ubuntu'
                                   '/precise/amd64/cm/archive.key')

DEFAULT_CDH5_CENTOS_REPO_LIST_URL = ('http://archive.cloudera.com/cdh5/redhat'
                                     '/6/x86_64/cdh/cloudera-cdh5.repo')

DEFAULT_CM5_CENTOS_REPO_LIST_URL = ('http://archive.cloudera.com/cm5/redhat'
                                    '/6/x86_64/cm/cloudera-manager.repo')

DEFAULT_SWIFT_LIB_URL = ('https://repository.cloudera.com/artifactory/repo/org'
                         '/apache/hadoop/hadoop-openstack/2.3.0-cdh5.1.0'
                         '/hadoop-openstack-2.3.0-cdh5.1.0.jar')

CDH5_REPO_URL = p.Config(
    'CDH5 repo list URL', 'general', 'cluster', priority=1,
    default_value="")

CDH5_REPO_KEY_URL = p.Config(
    'CDH5 repo key URL (for debian-based only)', 'general', 'cluster',
    priority=1, default_value="")

CM5_REPO_URL = p.Config(
    'CM5 repo list URL', 'general', 'cluster', priority=1,
    default_value="")

CM5_REPO_KEY_URL = p.Config(
    'CM5 repo key URL (for debian-based only)', 'general', 'cluster',
    priority=1, default_value="")

ENABLE_SWIFT = p.Config('Enable Swift', 'general', 'cluster',
                        config_type='bool', priority=1,
                        default_value=True)

SWIFT_LIB_URL = p.Config(
    'Hadoop OpenStack library URL', 'general', 'cluster', priority=1,
    default_value=DEFAULT_SWIFT_LIB_URL,
    description=("Library that adds Swift support to CDH. The file will be "
                 "downloaded from VM."))


def _get_cluster_plugin_configs():
    return [CDH5_REPO_URL, CDH5_REPO_KEY_URL, CM5_REPO_URL, CM5_REPO_KEY_URL,
            ENABLE_SWIFT, SWIFT_LIB_URL]


# ng wide configs

def _load_json(path_to_file):
    data = f.get_file_text(path_to_file)
    return json.loads(data)


path_to_config = 'plugins/cdh/resources/'
hdfs_confs = _load_json(path_to_config + 'hdfs-service.json')
namenode_confs = _load_json(path_to_config + 'hdfs-namenode.json')
datanode_confs = _load_json(path_to_config + 'hdfs-datanode.json')
secnamenode_confs = _load_json(path_to_config + 'hdfs-secondarynamenode.json')
yarn_confs = _load_json(path_to_config + 'yarn-service.json')
resourcemanager_confs = _load_json(
    path_to_config + 'yarn-resourcemanager.json')
nodemanager_confs = _load_json(path_to_config + 'yarn-nodemanager.json')
jobhistory_confs = _load_json(path_to_config + 'yarn-jobhistory.json')
oozie_service_confs = _load_json(path_to_config + 'oozie-service.json')
oozie_role_confs = _load_json(path_to_config + 'oozie-oozie.json')

priority_one_confs = _load_json(path_to_config + 'priority-one-confs.json')


def _prepare_value(value):
    if not value:
        return ""

    return value.replace('\n', ' ')


def _init_configs(confs, app_target, scope):
    cfgs = []
    for cfg in confs:
        priority = 1 if cfg['name'] in priority_one_confs else 2
        c = p.Config(cfg['name'], app_target, scope, priority=priority,
                     default_value=_prepare_value(cfg['value']),
                     description=cfg['desc'], is_optional=True)
        cfgs.append(c)

    return cfgs


def _get_ng_plugin_configs():
    cfg = []
    cfg += _init_configs(hdfs_confs, 'HDFS', 'cluster')
    cfg += _init_configs(namenode_confs, 'NAMENODE', 'node')
    cfg += _init_configs(datanode_confs, 'DATANODE', 'node')
    cfg += _init_configs(secnamenode_confs, 'SECONDARYNAMENODE', 'node')
    cfg += _init_configs(yarn_confs, 'YARN', 'cluster')
    cfg += _init_configs(resourcemanager_confs, 'RESOURCEMANAGER', 'node')
    cfg += _init_configs(nodemanager_confs, 'NODEMANAGER', 'node')
    cfg += _init_configs(jobhistory_confs, 'JOBHISTORY', 'node')
    cfg += _init_configs(oozie_service_confs, 'OOZIE', 'cluster')
    cfg += _init_configs(oozie_role_confs, 'OOZIE', 'node')
    return cfg


def get_plugin_configs():
    cluster_wide = _get_cluster_plugin_configs()
    ng_wide = _get_ng_plugin_configs()
    return cluster_wide + ng_wide


def _get_config_value(cluster, key):
    return cluster.cluster_configs.get(
        'general', {}).get(key.name, key.default_value)


def get_cdh5_repo_url(cluster):
    return _get_config_value(cluster, CDH5_REPO_URL)


def get_cdh5_key_url(cluster):
    return _get_config_value(cluster, CDH5_REPO_KEY_URL)


def get_cm5_repo_url(cluster):
    return _get_config_value(cluster, CM5_REPO_URL)


def get_cm5_key_url(cluster):
    return _get_config_value(cluster, CM5_REPO_KEY_URL)


def is_swift_enabled(cluster):
    return _get_config_value(cluster, ENABLE_SWIFT)


def get_swift_lib_url(cluster):
    return _get_config_value(cluster, SWIFT_LIB_URL)
