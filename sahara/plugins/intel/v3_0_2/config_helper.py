# Copyright (c) 2013 Intel Corporation
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

from sahara.plugins import provisioning as p
from sahara.utils import xmlutils as x


CORE_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/intel/v3_0_2/resources/hadoop-default.xml')

HDFS_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/intel/v3_0_2/resources/hdfs-default.xml')

YARN_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/intel/v3_0_2/resources/yarn-default.xml')

OOZIE_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/intel/v3_0_2/resources/oozie-default.xml')


XML_CONFS = {
    "Hadoop": [CORE_DEFAULT],
    "HDFS": [HDFS_DEFAULT],
    "YARN": [YARN_DEFAULT],
    "JobFlow": [OOZIE_DEFAULT]
}

IDH_TARBALL_URL = p.Config('IDH tarball URL', 'general', 'cluster', priority=1,
                           default_value='http://repo2.intelhadoop.com/'
                                         'setup/setup-intelhadoop-'
                                         '3.0.2-en-evaluation.RHEL.tar.gz')

OS_REPO_URL = p.Config('OS repository URL', 'general', 'cluster', priority=1,
                       is_optional=True,
                       default_value='http://mirror.centos.org/'
                                     'centos-6/6/os/x86_64')

IDH_REPO_URL = p.Config('IDH repository URL', 'general', 'cluster',
                        priority=1, is_optional=True,
                        default_value='http://repo2.intelhadoop.com'
                                      '/evaluation/en/RHEL/3.0.2/rpm')

OOZIE_EXT22_URL = p.Config(
    'Ext 2.2 URL', 'general', 'cluster',
    description='Ext 2.2 library is required for Oozie Web Console. '
                'The file will be downloaded from VM with oozie.',
    priority=1, is_optional=True,
    default_value='http://extjs.com/deploy/ext-2.2.zip')

ENABLE_SWIFT = p.Config('Enable Swift', 'general', 'cluster',
                        config_type="bool", priority=1,
                        default_value=True, is_optional=True)

HADOOP_SWIFTFS_JAR_URL = p.Config(
    'Hadoop SwiftFS jar URL', 'general', 'cluster',
    description='Library that adds swift support to hadoop. '
                'The file will be downloaded from VM with oozie.',
    priority=1, is_optional=True,
    default_value='http://sahara-files.mirantis.com/'
                  'hadoop-swift/hadoop-swift-latest.jar')

HIDDEN_CONFS = ['fs.default.name', 'dfs.namenode.name.dir',
                'dfs.datanode.data.dir']

CLUSTER_WIDE_CONFS = ['dfs.block.size', 'dfs.permissions', 'dfs.replication',
                      'dfs.replication.min', 'dfs.replication.max',
                      'io.file.buffer.size']

PRIORITY_1_CONFS = ['dfs.datanode.du.reserved',
                    'dfs.datanode.failed.volumes.tolerated',
                    'dfs.datanode.max.xcievers', 'dfs.datanode.handler.count',
                    'dfs.namenode.handler.count'
                    'io.sort.mb']

PRIORITY_1_CONFS += CLUSTER_WIDE_CONFS

CFG_TYPE = {
    "Boolean": "bool",
    "String": "string",
    "Integer": "int",
    "Choose": "string",
    "Class": "string",
    "Directory": "string",
    "Float": "string",
    "Int_range": "string",
}


def _initialise_configs():
    configs = []

    for service, config_lists in XML_CONFS.iteritems():
        for config_list in config_lists:
            for config in config_list:
                if config['name'] not in HIDDEN_CONFS:
                    cfg = p.Config(
                        config['name'], service, "cluster", is_optional=True,
                        config_type="string",
                        default_value=str(config['value']),
                        description=config['description'])

                    if config.get('type'):
                        cfg.config_type = CFG_TYPE[config['type']]
                    if cfg.config_type == 'bool':
                        cfg.default_value = cfg.default_value == 'true'
                    if cfg.config_type == 'int':
                        if cfg.default_value:
                            cfg.default_value = int(cfg.default_value)
                        else:
                            cfg.config_type = 'string'
                    if config['name'] in PRIORITY_1_CONFS:
                        cfg.priority = 1
                    configs.append(cfg)

    configs.append(IDH_TARBALL_URL)
    configs.append(IDH_REPO_URL)
    configs.append(OS_REPO_URL)
    configs.append(OOZIE_EXT22_URL)
    configs.append(ENABLE_SWIFT)
    return configs


PLUGIN_CONFIGS = _initialise_configs()


def get_plugin_configs():
    return PLUGIN_CONFIGS


def get_config_value(cluster_configs, key):
    if not cluster_configs or cluster_configs.get(key.name) is None:
        return key.default_value
    return cluster_configs.get(key.name)
