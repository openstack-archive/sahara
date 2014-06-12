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

from oslo.config import cfg

from sahara import exceptions as ex
from sahara.openstack.common import log as logging
from sahara.plugins import provisioning as p
from sahara.utils import types as types
from sahara.utils import xmlutils as x

CONF = cfg.CONF
CONF.import_opt("enable_data_locality", "sahara.topology.topology_helper")

LOG = logging.getLogger(__name__)

CORE_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/v2_3_0/resources/core-default.xml')

HDFS_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/v2_3_0/resources/hdfs-default.xml')

MAPRED_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/v2_3_0/resources/mapred-default.xml')

YARN_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/v2_3_0/resources/yarn-default.xml')

OOZIE_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/v2_3_0/resources/oozie-default.xml')

XML_CONFS = {
    "Hadoop": [CORE_DEFAULT],
    "HDFS": [HDFS_DEFAULT],
    "YARN": [YARN_DEFAULT],
    "MapReduce": [MAPRED_DEFAULT],
    "JobFlow": [OOZIE_DEFAULT]
}

ENV_CONFS = {
    "YARN": {
        'ResourceManager Heap Size': 1024,
        'NodeManager Heap Size': 1024
    },
    "HDFS": {
        'NameNode Heap Size': 1024,
        'SecondaryNameNode Heap Size': 1024,
        'DataNode Heap Size': 1024
    },
    "MapReduce": {
        'JobHistoryServer Heap Size': 1024
    },
    "JobFlow": {
        'Oozie Heap Size': 1024
    }
}

ENABLE_SWIFT = p.Config('Enable Swift', 'general', 'cluster',
                        config_type="bool", priority=1,
                        default_value=True, is_optional=False)

ENABLE_MYSQL = p.Config('Enable MySQL', 'general', 'cluster',
                        config_type="bool", priority=1,
                        default_value=True, is_optional=True)

ENABLE_DATA_LOCALITY = p.Config('Enable Data Locality', 'general', 'cluster',
                                config_type="bool", priority=1,
                                default_value=True, is_optional=True)

HIDDEN_CONFS = [
    'dfs.hosts',
    'dfs.hosts.exclude',
    'dfs.namenode.data.dir',
    'dfs.namenode.name.dir',
    'fs.default.name',
    'fs.defaultFS',
    'fs.swift.impl',
    'hadoop.proxyuser.hadoop.groups',
    'hadoop.proxyuser.hadoop.hosts',
    'mapreduce.framework.name',
    'mapreduce.jobhistory.address',
    'mapreduce.jobhistory.done.dir',
    'mapreduce.jobhistory.intermediate-done-dir',
    'mapreduce.jobhistory.webapp.address',
    'yarn.nodemanager.aux-services',
    'yarn.resourcemanager.address',
    'yarn.resourcemanager.admin.address',
    'yarn.resourcemanager.hostname',
    'yarn.resourcemanager.nodes.exclude-path',
    'yarn.resourcemanager.nodes.include-path',
    'yarn.resourcemanager.resource-tracker.address',
    'yarn.resourcemanager.scheduler.address',
    'yarn.resourcemanager.webapp.address'
]

CLUSTER_WIDE_CONFS = [
    'dfs.blocksize', 'dfs.namenode.replication.min', 'dfs.permissions.enabled',
    'dfs.replication', 'dfs.replication.max', 'io.compression.codecs',
    'io.file.buffer.size', 'mapreduce.job.counters.max',
    'mapreduce.map.output.compress.codec',
    'mapreduce.output.fileoutputformat.compress.codec',
    'mapreduce.output.fileoutputformat.compress.type',
    'mapredude.map.output.compress',
    'mapredude.output.fileoutputformat.compress'
]

PRIORITY_1_CONFS = [
    'dfs.datanode.du.reserved',
    'dfs.datanode.failed.volumes.tolerated',
    'dfs.datanode.handler.count',
    'dfs.datanode.max.transfer.threads',
    'dfs.namenode.handler.count',
    'mapred.child.java.opts',
    'mapred.jobtracker.maxtasks.per.job',
    'mapreduce.jobtracker.handler.count',
    'mapreduce.map.java.opts',
    'mapreduce.reduce.java.opts',
    'mapreduce.task.io.sort.mb',
    'mapreduce.tasktracker.map.tasks.maximum',
    'mapreduce.tasktracker.reduce.tasks.maximum',
    'yarn.nodemanager.resource.cpu-vcores',
    'yarn.nodemanager.resource.memory-mb',
    'yarn.scheduler.maximum-allocation-mb',
    'yarn.scheduler.maximum-allocation-vcores',
    'yarn.scheduler.minimum-allocation-mb',
    'yarn.scheduler.minimum-allocation-vcores'
]

# for now we have not so many cluster-wide configs
# lets consider all of them having high priority
PRIORITY_1_CONFS += CLUSTER_WIDE_CONFS


def _init_xml_configs():
    configs = []
    for service, config_lists in XML_CONFS.iteritems():
        for config_list in config_lists:
            for config in config_list:
                if config['name'] not in HIDDEN_CONFS:
                    cfg = p.Config(config['name'], service, "node",
                                   is_optional=True, config_type="string",
                                   default_value=str(config['value']),
                                   description=config['description'])
                    if cfg.default_value in ["true", "false"]:
                        cfg.config_type = "bool"
                        cfg.default_value = (cfg.default_value == 'true')
                    elif types.is_int(cfg.default_value):
                        cfg.config_type = "int"
                        cfg.default_value = int(cfg.default_value)
                    if config['name'] in CLUSTER_WIDE_CONFS:
                        cfg.scope = 'cluster'
                    if config['name'] in PRIORITY_1_CONFS:
                        cfg.priority = 1
                    configs.append(cfg)

    return configs


def _init_env_configs():
    configs = []
    for service, config_items in ENV_CONFS.iteritems():
        for name, value in config_items.iteritems():
            configs.append(p.Config(name, service, "node",
                                    default_value=value, priority=1,
                                    config_type="int"))

    return configs


def _init_general_configs():
    configs = [ENABLE_SWIFT, ENABLE_MYSQL]
    if CONF.enable_data_locality:
        configs.append(ENABLE_DATA_LOCALITY)
    return configs


# Initialise plugin Hadoop configurations
PLUGIN_XML_CONFIGS = _init_xml_configs()
PLUGIN_ENV_CONFIGS = _init_env_configs()
PLUGIN_GENERAL_CONFIGS = _init_general_configs()


def _init_all_configs():
    configs = []
    configs.extend(PLUGIN_XML_CONFIGS)
    configs.extend(PLUGIN_ENV_CONFIGS)
    configs.extend(PLUGIN_GENERAL_CONFIGS)
    return configs


PLUGIN_CONFIGS = _init_all_configs()


def get_plugin_configs():
    return PLUGIN_CONFIGS


def get_xml_configs():
    return PLUGIN_XML_CONFIGS


def get_env_configs():
    return ENV_CONFS


def get_config_value(service, name, cluster=None):
    if cluster:
        for ng in cluster.node_groups:
            cl_param = ng.configuration().get(service, {}).get(name)
            if cl_param is not None:
                return cl_param

    for c in get_plugin_configs():
        if c.applicable_target == service and c.name == name:
            return c.default_value

    raise ex.NotFoundException(
        name, "Unable to get parameter '%s' from service %s" % (name, service))


def is_mysql_enabled(cluster):
    return get_config_value(
        ENABLE_MYSQL.applicable_target, ENABLE_MYSQL.name, cluster)


def is_data_locality_enabled(cluster):
    if not CONF.enable_data_locality:
        return False
    return get_config_value(ENABLE_DATA_LOCALITY.applicable_target,
                            ENABLE_DATA_LOCALITY.name, cluster)
