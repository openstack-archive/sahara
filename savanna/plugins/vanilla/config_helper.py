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

import pkg_resources as pkg
import xml.dom.minidom as xml

import jinja2 as j2

from savanna.plugins import provisioning as p
from savanna import version


def _load_xml_default_configs(file_name):
    doc = xml.parse(
        pkg.resource_filename(version.version_info.package,
                              'plugins/vanilla/resources/%s' % file_name)
    )

    properties = doc.getElementsByTagName("name")
    return [prop.childNodes[0].data for prop in properties]


CORE_DEFAULT = _load_xml_default_configs('core-default.xml')
HDFS_DEFAULT = _load_xml_default_configs('hdfs-default.xml')
MAPRED_DEFAULT = _load_xml_default_configs('mapred-default.xml')

XML_CONFS = {
    "HDFS": [CORE_DEFAULT, HDFS_DEFAULT],
    "MAPREDUCE": [MAPRED_DEFAULT]
}

# TODO(aignatov): Environmental configs could be more complex
ENV_CONFS = {
    "MAPREDUCE": {
        'job_tracker_heap_size': 'HADOOP_JOBTRACKER_OPTS=\\"-Xmx%sm\\"',
        'task_tracker_heap_size': 'HADOOP_TASKTRACKER_OPTS=\\"-Xmx%sm\\"'
    },
    "HDFS": {
        'name_node_heap_size': 'HADOOP_NAMENODE_OPTS=\\"-Xmx%sm\\"',
        'data_node_heap_size': 'HADOOP_DATANODE_OPTS=\\"-Xmx%sm\\"'
    }
}


def _initialise_configs():
    configs = []
    for service, config_lists in XML_CONFS.iteritems():
        for config_list in config_lists:
            for config_name in config_list:
                # TODO(aignatov): Need to add default values and types
                configs.append(
                    p.Config(config_name, service, "node", is_optional=True))

    for service, config_items in ENV_CONFS.iteritems():
        for name, param_format_str in config_items.iteritems():
            configs.append(p.Config(name, service, "node", default_value=1024))

    return configs

# Initialise plugin Hadoop configurations
PLUGIN_CONFIGS = _initialise_configs()


def get_plugin_configs():
    return PLUGIN_CONFIGS


def _create_xml(configs, global_conf):
    doc = xml.Document()

    pi = doc.createProcessingInstruction('xml-stylesheet',
                                         'type="text/xsl" '
                                         'href="configuration.xsl"')
    doc.insertBefore(pi, doc.firstChild)

    # Create the <configuration> base element
    configuration = doc.createElement("configuration")
    doc.appendChild(configuration)

    for prop_name, prop_value in configs.items():
        if prop_name in global_conf:
            # Create the <property> element
            property = doc.createElement("property")
            configuration.appendChild(property)

            # Create a <name> element in <property>
            name = doc.createElement("name")
            property.appendChild(name)

            # Give the <name> element some hadoop config name
            name_text = doc.createTextNode(prop_name)
            name.appendChild(name_text)

            # Create a <value> element in <property>
            value = doc.createElement("value")
            property.appendChild(value)

            # Give the <value> element some hadoop config value
            value_text = doc.createTextNode(prop_value)
            value.appendChild(value_text)

    # Return newly created XML
    return doc.toprettyxml(indent="  ")


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
        'core-site': _create_xml(cfg, CORE_DEFAULT),
        'mapred-site': _create_xml(cfg, MAPRED_DEFAULT),
        'hdfs-site': _create_xml(cfg, HDFS_DEFAULT)
    }

    return xml_configs


def extract_environment_confs(configs):
    """Returns list of Hadoop parameters which should be passed via environment
    """
    lst = []
    for service, srv_confs in configs.items():
        for param_name, param_value in srv_confs.items():
            for cfg_name, cfg_format_str in ENV_CONFS[service].items():
                if param_name == cfg_name and param_value is not None:
                    lst.append(cfg_format_str % param_value)
    return lst


def extract_xml_confs(configs):
    """Returns list of Hadoop parameters which should be passed into general
    configs like core-site.xml
    """
    lst = []
    for service, srv_confs in configs.items():
        for param_name, param_value in srv_confs.items():
            for cfg_list in XML_CONFS[service]:
                if param_name in cfg_list and param_value is not None:
                    lst.append((param_name, param_value))
    return lst


env = j2.Environment(loader=j2.PackageLoader('savanna',
                                             'plugins/vanilla/resources'))


def render_template(template_name, **kwargs):
    template = env.get_template('%s.template' % template_name)
    return template.render(**kwargs)
