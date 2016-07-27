# Copyright (c) 2015 Mirantis Inc.
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

from oslo_config import cfg
from oslo_log import log as logging
import six

from sahara.plugins import provisioning as p
from sahara.plugins.vanilla.hadoop2 import config_helper as c_helper
from sahara.utils import xmlutils as x

CONF = cfg.CONF
CONF.import_opt("enable_data_locality", "sahara.topology.topology_helper")

LOG = logging.getLogger(__name__)

CORE_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/v2_7_1/resources/core-default.xml')

HDFS_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/v2_7_1/resources/hdfs-default.xml')

MAPRED_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/v2_7_1/resources/mapred-default.xml')

YARN_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/v2_7_1/resources/yarn-default.xml')

OOZIE_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/v2_7_1/resources/oozie-default.xml')

HIVE_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/v2_7_1/resources/hive-default.xml')

XML_CONFS = {
    "Hadoop": [CORE_DEFAULT],
    "HDFS": [HDFS_DEFAULT],
    "YARN": [YARN_DEFAULT],
    "MapReduce": [MAPRED_DEFAULT],
    "JobFlow": [OOZIE_DEFAULT],
    "Hive": [HIVE_DEFAULT]
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

# Initialise plugin Hadoop configurations
PLUGIN_XML_CONFIGS = c_helper.init_xml_configs(XML_CONFS)
PLUGIN_ENV_CONFIGS = c_helper.init_env_configs(ENV_CONFS)


def _init_all_configs():
    configs = []
    configs.extend(PLUGIN_XML_CONFIGS)
    configs.extend(PLUGIN_ENV_CONFIGS)
    configs.extend(c_helper.PLUGIN_GENERAL_CONFIGS)
    configs.extend(_get_spark_configs())
    return configs


def _get_spark_configs():
    spark_configs = []
    for service, config_items in six.iteritems(c_helper.SPARK_CONFS):
        for item in config_items['OPTIONS']:
            cfg = p.Config(name=item["name"],
                           description=item["description"],
                           default_value=item["default"],
                           applicable_target=service,
                           scope="cluster", is_optional=True,
                           priority=item["priority"])
            spark_configs.append(cfg)
    return spark_configs


PLUGIN_CONFIGS = _init_all_configs()


def get_plugin_configs():
    return PLUGIN_CONFIGS


def get_xml_configs():
    return PLUGIN_XML_CONFIGS


def get_env_configs():
    return ENV_CONFS
