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

import six

from sahara.i18n import _LI
from sahara.openstack.common import log as logging
from sahara.plugins.vanilla.hadoop2 import config_helper as c_helper
from sahara.plugins.vanilla.hadoop2 import oozie_helper as o_helper
from sahara.plugins.vanilla import utils as vu
from sahara.swift import swift_helper as swift
from sahara.topology import topology_helper as th
from sahara.utils import files as f
from sahara.utils import xmlutils as x

LOG = logging.getLogger(__name__)

HADOOP_CONF_DIR = '/opt/hadoop/etc/hadoop'
OOZIE_CONF_DIR = '/opt/oozie/conf'
HADOOP_USER = 'hadoop'
HADOOP_GROUP = 'hadoop'


def configure_cluster(pctx, cluster):
    LOG.debug("Configuring cluster \"%s\"", cluster.name)
    instances = []
    for node_group in cluster.node_groups:
        for instance in node_group.instances:
            instances.append(instance)

    configure_instances(pctx, instances)
    configure_topology_data(pctx, cluster)


def configure_instances(pctx, instances):
    for instance in instances:
        _provisioning_configs(pctx, instance)
        _post_configuration(pctx, instance)


def _provisioning_configs(pctx, instance):
    xmls, env = _generate_configs(pctx, instance.node_group)
    _push_xml_configs(instance, xmls)
    _push_env_configs(instance, env)


def _generate_configs(pctx, node_group):
    hadoop_xml_confs = _get_hadoop_configs(pctx, node_group)
    user_xml_confs, user_env_confs = _get_user_configs(pctx, node_group)
    xml_confs = _merge_configs(user_xml_confs, hadoop_xml_confs)
    env_confs = _merge_configs(pctx['env_confs'], user_env_confs)

    return xml_confs, env_confs


def _get_hadoop_configs(pctx, node_group):
    cluster = node_group.cluster
    nn_hostname = vu.get_instance_hostname(vu.get_namenode(cluster))
    dirs = _get_hadoop_dirs(node_group)
    confs = {
        'Hadoop': {
            'fs.defaultFS': 'hdfs://%s:9000' % nn_hostname
        },
        'HDFS': {
            'dfs.namenode.name.dir': ','.join(dirs['hadoop_name_dirs']),
            'dfs.datanode.data.dir': ','.join(dirs['hadoop_data_dirs']),
            'dfs.hosts': '%s/dn-include' % HADOOP_CONF_DIR,
            'dfs.hosts.exclude': '%s/dn-exclude' % HADOOP_CONF_DIR
        }
    }

    res_hostname = vu.get_instance_hostname(vu.get_resourcemanager(cluster))
    if res_hostname:
        confs['YARN'] = {
            'yarn.nodemanager.aux-services': 'mapreduce_shuffle',
            'yarn.resourcemanager.hostname': '%s' % res_hostname,
            'yarn.resourcemanager.nodes.include-path': '%s/nm-include' % (
                HADOOP_CONF_DIR),
            'yarn.resourcemanager.nodes.exclude-path': '%s/nm-exclude' % (
                HADOOP_CONF_DIR)
        }
        confs['MapReduce'] = {
            'mapreduce.framework.name': 'yarn'
        }
        hs_hostname = vu.get_instance_hostname(vu.get_historyserver(cluster))
        if hs_hostname:
            confs['MapReduce']['mapreduce.jobhistory.address'] = (
                "%s:10020" % hs_hostname)

    oozie = vu.get_oozie(cluster)
    if oozie:
        hadoop_cfg = {
            'hadoop.proxyuser.hadoop.hosts': '*',
            'hadoop.proxyuser.hadoop.groups': 'hadoop'
        }
        confs['Hadoop'].update(hadoop_cfg)

        oozie_cfg = o_helper.get_oozie_required_xml_configs(HADOOP_CONF_DIR)
        if c_helper.is_mysql_enabled(pctx, cluster):
            oozie_cfg.update(o_helper.get_oozie_mysql_configs())

        confs['JobFlow'] = oozie_cfg

    if c_helper.is_swift_enabled(pctx, cluster):
        swift_configs = {}
        for config in swift.get_swift_configs():
            swift_configs[config['name']] = config['value']

        confs['Hadoop'].update(swift_configs)

    if c_helper.is_data_locality_enabled(pctx, cluster):
        confs['Hadoop'].update(th.TOPOLOGY_CONFIG)
        confs['Hadoop'].update({"topology.script.file.name":
                                HADOOP_CONF_DIR + "/topology.sh"})

    return confs


def _get_user_configs(pctx, node_group):
    ng_xml_confs, ng_env_confs = _separate_configs(node_group.node_configs,
                                                   pctx['env_confs'])
    cl_xml_confs, cl_env_confs = _separate_configs(
        node_group.cluster.cluster_configs, pctx['env_confs'])

    xml_confs = _merge_configs(cl_xml_confs, ng_xml_confs)
    env_confs = _merge_configs(cl_env_confs, ng_env_confs)
    return xml_confs, env_confs


def _separate_configs(configs, all_env_configs):
    xml_configs = {}
    env_configs = {}
    for service, params in six.iteritems(configs):
        xml_configs[service] = {}
        env_configs[service] = {}
        for param, value in six.iteritems(params):
            if all_env_configs.get(service, {}).get(param):
                if not env_configs.get(service):
                    env_configs[service] = {}
                env_configs[service][param] = value
            else:
                if not xml_configs.get(service):
                    xml_configs[service] = {}
                xml_configs[service][param] = value

    return xml_configs, env_configs


def _generate_xml(configs):
    xml_confs = {}
    for service, confs in six.iteritems(configs):
        xml_confs[service] = x.create_hadoop_xml(confs)

    return xml_confs


def _push_env_configs(instance, configs):
    nn_heap = configs['HDFS']['NameNode Heap Size']
    snn_heap = configs['HDFS']['SecondaryNameNode Heap Size']
    dn_heap = configs['HDFS']['DataNode Heap Size']
    rm_heap = configs['YARN']['ResourceManager Heap Size']
    nm_heap = configs['YARN']['NodeManager Heap Size']
    hs_heap = configs['MapReduce']['JobHistoryServer Heap Size']

    with instance.remote() as r:
        r.replace_remote_string(
            '%s/hadoop-env.sh' % HADOOP_CONF_DIR,
            'export HADOOP_NAMENODE_OPTS=.*',
            'export HADOOP_NAMENODE_OPTS="-Xmx%dm"' % nn_heap)
        r.replace_remote_string(
            '%s/hadoop-env.sh' % HADOOP_CONF_DIR,
            'export HADOOP_SECONDARYNAMENODE_OPTS=.*',
            'export HADOOP_SECONDARYNAMENODE_OPTS="-Xmx%dm"' % snn_heap)
        r.replace_remote_string(
            '%s/hadoop-env.sh' % HADOOP_CONF_DIR,
            'export HADOOP_DATANODE_OPTS=.*',
            'export HADOOP_DATANODE_OPTS="-Xmx%dm"' % dn_heap)
        r.replace_remote_string(
            '%s/yarn-env.sh' % HADOOP_CONF_DIR,
            '\\#export YARN_RESOURCEMANAGER_HEAPSIZE=.*',
            'export YARN_RESOURCEMANAGER_HEAPSIZE=%d' % rm_heap)
        r.replace_remote_string(
            '%s/yarn-env.sh' % HADOOP_CONF_DIR,
            '\\#export YARN_NODEMANAGER_HEAPSIZE=.*',
            'export YARN_NODEMANAGER_HEAPSIZE=%d' % nm_heap)
        r.replace_remote_string(
            '%s/mapred-env.sh' % HADOOP_CONF_DIR,
            'export HADOOP_JOB_HISTORYSERVER_HEAPSIZE=.*',
            'export HADOOP_JOB_HISTORYSERVER_HEAPSIZE=%d' % hs_heap)


def _push_xml_configs(instance, configs):
    xmls = _generate_xml(configs)
    service_to_conf_map = {
        'Hadoop': '%s/core-site.xml' % HADOOP_CONF_DIR,
        'HDFS': '%s/hdfs-site.xml' % HADOOP_CONF_DIR,
        'YARN': '%s/yarn-site.xml' % HADOOP_CONF_DIR,
        'MapReduce': '%s/mapred-site.xml' % HADOOP_CONF_DIR,
        'JobFlow': '%s/oozie-site.xml' % OOZIE_CONF_DIR
    }
    xml_confs = {}
    for service, confs in six.iteritems(xmls):
        if service not in service_to_conf_map.keys():
            continue

        xml_confs[service_to_conf_map[service]] = confs

    _push_configs_to_instance(instance, xml_confs)


def _push_configs_to_instance(instance, configs):
    LOG.debug("Push configs to instance \"%s\"", instance.instance_name)
    with instance.remote() as r:
        for fl, data in six.iteritems(configs):
            r.write_file_to(fl, data, run_as_root=True)


def _post_configuration(pctx, instance):
    node_group = instance.node_group
    dirs = _get_hadoop_dirs(node_group)
    args = {
        'hadoop_user': HADOOP_USER,
        'hadoop_group': HADOOP_GROUP,
        'hadoop_conf_dir': HADOOP_CONF_DIR,
        'oozie_conf_dir': OOZIE_CONF_DIR,
        'hadoop_name_dirs': " ".join(dirs['hadoop_name_dirs']),
        'hadoop_data_dirs': " ".join(dirs['hadoop_data_dirs']),
        'hadoop_log_dir': dirs['hadoop_log_dir'],
        'hadoop_secure_dn_log_dir': dirs['hadoop_secure_dn_log_dir'],
        'yarn_log_dir': dirs['yarn_log_dir']
    }
    post_conf_script = f.get_file_text(
        'plugins/vanilla/hadoop2/resources/post_conf.template')
    post_conf_script = post_conf_script.format(**args)

    with instance.remote() as r:
        r.write_file_to('/tmp/post_conf.sh', post_conf_script)
        r.execute_command('chmod +x /tmp/post_conf.sh')
        r.execute_command('sudo /tmp/post_conf.sh')

        if c_helper.is_data_locality_enabled(pctx,
                                             instance.node_group.cluster):
            t_script = HADOOP_CONF_DIR + '/topology.sh'
            r.write_file_to(t_script, f.get_file_text(
                            'plugins/vanilla/hadoop2/resources/topology.sh'),
                            run_as_root=True)
            r.execute_command('chmod +x ' + t_script, run_as_root=True)


def _get_hadoop_dirs(node_group):
    dirs = {}
    storage_paths = node_group.storage_paths()
    dirs['hadoop_name_dirs'] = _make_hadoop_paths(
        storage_paths, '/hdfs/namenode')
    dirs['hadoop_data_dirs'] = _make_hadoop_paths(
        storage_paths, '/hdfs/datanode')
    dirs['hadoop_log_dir'] = _make_hadoop_paths(
        storage_paths, '/hadoop/logs')[0]
    dirs['hadoop_secure_dn_log_dir'] = _make_hadoop_paths(
        storage_paths, '/hadoop/logs/secure')[0]
    dirs['yarn_log_dir'] = _make_hadoop_paths(
        storage_paths, '/yarn/logs')[0]

    return dirs


def _make_hadoop_paths(paths, hadoop_dir):
    return [path + hadoop_dir for path in paths]


def _merge_configs(a, b):
    res = {}

    def update(cfg):
        for service, configs in six.iteritems(cfg):
            if not res.get(service):
                res[service] = {}

            res[service].update(configs)

    update(a)
    update(b)
    return res


def configure_topology_data(pctx, cluster):
    if c_helper.is_data_locality_enabled(pctx, cluster):
        LOG.info(_LI("Node group awareness is not implemented in YARN yet "
                     "so enable_hypervisor_awareness set to False explicitly"))
        tpl_map = th.generate_topology_map(cluster, is_node_awareness=False)
        topology_data = "\n".join(
            [k + " " + v for k, v in tpl_map.items()]) + "\n"
        for ng in cluster.node_groups:
            for i in ng.instances:
                i.remote().write_file_to(HADOOP_CONF_DIR + "/topology.data",
                                         topology_data, run_as_root=True)


def get_open_ports(node_group):
    ports = []

    if "namenode" in node_group.node_processes:
        ports.append(50070)
        ports.append(9000)

    if "secondarynamenode" in node_group.node_processes:
        ports.append(50090)

    if "resourcemanager" in node_group.node_processes:
        ports.append(8088)
        ports.append(8032)

    if "historyserver" in node_group.node_processes:
        ports.append(19888)

    if "datanode" in node_group.node_processes:
        ports.append(50010)
        ports.append(50075)
        ports.append(50020)

    if "nodemanager" in node_group.node_processes:
        ports.append(8042)

    if "oozie" in node_group.node_processes:
        ports.append(11000)

    return ports
