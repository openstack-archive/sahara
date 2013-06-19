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

import jinja2 as j2

from savanna.openstack.common import log as logging
from savanna.plugins import provisioning as p
from savanna.utils import xmlutils as x

LOG = logging.getLogger(__name__)

CORE_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/resources/core-default.xml')

HDFS_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/resources/hdfs-default.xml')

MAPRED_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/resources/mapred-default.xml')

XML_CONFS = {
    "HDFS": [CORE_DEFAULT, HDFS_DEFAULT],
    "MAPREDUCE": [MAPRED_DEFAULT]
}

# TODO(aignatov): Environmental configs could be more complex
ENV_CONFS = {
    "MAPREDUCE": {
        'Job Tracker Heap Size': 'HADOOP_JOBTRACKER_OPTS=\\"-Xmx%sm\\"',
        'Task Tracker Heap Size': 'HADOOP_TASKTRACKER_OPTS=\\"-Xmx%sm\\"'
    },
    "HDFS": {
        'Name Node Heap Size': 'HADOOP_NAMENODE_OPTS=\\"-Xmx%sm\\"',
        'Data Node Heap Size': 'HADOOP_DATANODE_OPTS=\\"-Xmx%sm\\"'
    }
}

HIDDEN_CONFS = ['fs.default.name', 'dfs.name.dir', 'dfs.data.dir',
                'mapred.job.tracker', 'mapred.system.dir', 'mapred.local.dir']


def _initialise_configs():
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
                    if str(cfg.default_value).isdigit():
                        cfg.config_type = "int"
                        cfg.default_value = int(cfg.default_value)
                    configs.append(cfg)

    for service, config_items in ENV_CONFS.iteritems():
        for name, param_format_str in config_items.iteritems():
            configs.append(p.Config(name, service, "node",
                                    default_value=1024, priority=1,
                                    config_type="int"))

    return configs

# Initialise plugin Hadoop configurations
PLUGIN_CONFIGS = _initialise_configs()


def get_plugin_configs():
    return PLUGIN_CONFIGS


def generate_xml_configs(configs, nn_hostname, jt_hostname=None):
    # inserting common configs depends on provisioned VMs and HDFS placement
    # TODO(aignatov): should be moved to cluster context
    cfg = {
        'fs.default.name': 'hdfs://%s:8020' % nn_hostname,
        'dfs.name.dir': '/mnt/lib/hadoop/hdfs/namenode',
        'dfs.data.dir': '/mnt/lib/hadoop/hdfs/datanode',
    }

    if jt_hostname:
        mr_cfg = {
            'mapred.job.tracker': '%s:8021' % jt_hostname,
            'mapred.system.dir': '/mnt/mapred/mapredsystem',
            'mapred.local.dir': '/mnt/lib/hadoop/mapred'
        }
        cfg.update(mr_cfg)

    # inserting user-defined configs
    for key, value in extract_xml_confs(configs):
        cfg[key] = value

    # invoking applied configs to appropriate xml files
    xml_configs = {
        'core-site': x.create_hadoop_xml(cfg, CORE_DEFAULT),
        'mapred-site': x.create_hadoop_xml(cfg, MAPRED_DEFAULT),
        'hdfs-site': x.create_hadoop_xml(cfg, HDFS_DEFAULT)
    }

    return xml_configs


def extract_environment_confs(configs):
    """Returns list of Hadoop parameters which should be passed via environment
    """
    lst = []
    for service, srv_confs in configs.items():
        if ENV_CONFS.get(service):
            for param_name, param_value in srv_confs.items():
                for cfg_name, cfg_format_str in ENV_CONFS[service].items():
                    if param_name == cfg_name and param_value is not None:
                        lst.append(cfg_format_str % param_value)
        else:
            LOG.warn("Plugin recieved wrong applicable target '%s' in "
                     "environmental configs" % service)
    return lst


def extract_xml_confs(configs):
    """Returns list of Hadoop parameters which should be passed into general
    configs like core-site.xml
    """
    lst = []
    for service, srv_confs in configs.items():
        if XML_CONFS.get(service):
            for param_name, param_value in srv_confs.items():
                for cfg_list in XML_CONFS[service]:
                    names = [cfg['name'] for cfg in cfg_list]
                    if param_name in names and param_value is not None:
                        lst.append((param_name, param_value))
        else:
            LOG.warn("Plugin recieved wrong applicable target '%s' for "
                     "xml configs" % service)
    return lst


env = j2.Environment(loader=j2.PackageLoader('savanna',
                                             'plugins/vanilla/resources'))


def render_template(template_name, **kwargs):
    template = env.get_template('%s.template' % template_name)
    return template.render(**kwargs)
