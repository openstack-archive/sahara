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

from oslo_config import cfg
from oslo_log import log as logging

from sahara import conductor as c
from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.i18n import _LW
from sahara.plugins import provisioning as p
from sahara.plugins import utils
from sahara.plugins.vanilla import utils as vu
from sahara.plugins.vanilla.v1_2_1 import mysql_helper as m_h
from sahara.plugins.vanilla.v1_2_1 import oozie_helper as o_h
from sahara.swift import swift_helper as swift
from sahara.topology import topology_helper as topology
from sahara.utils import crypto
from sahara.utils import types as types
from sahara.utils import xmlutils as x


conductor = c.API
LOG = logging.getLogger(__name__)
CONF = cfg.CONF

CORE_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/v1_2_1/resources/core-default.xml')

HDFS_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/v1_2_1/resources/hdfs-default.xml')

MAPRED_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/v1_2_1/resources/mapred-default.xml')

HIVE_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/vanilla/v1_2_1/resources/hive-default.xml')

# Append Oozie configs fore core-site.xml
CORE_DEFAULT += o_h.OOZIE_CORE_DEFAULT

XML_CONFS = {
    "HDFS": [CORE_DEFAULT, HDFS_DEFAULT],
    "MapReduce": [MAPRED_DEFAULT],
    "JobFlow": [o_h.OOZIE_DEFAULT],
    "Hive": [HIVE_DEFAULT]
}

ENV_CONFS = {
    "MapReduce": {
        'Job Tracker Heap Size': 'HADOOP_JOBTRACKER_OPTS=\\"-Xmx%sm\\"',
        'Task Tracker Heap Size': 'HADOOP_TASKTRACKER_OPTS=\\"-Xmx%sm\\"'
    },
    "HDFS": {
        'Name Node Heap Size': 'HADOOP_NAMENODE_OPTS=\\"-Xmx%sm\\"',
        'Secondary Name Node Heap Size': 'HADOOP_SECONDARYNAMENODE_OPTS='
                                         '\\"-Xmx%sm\\"',
        'Data Node Heap Size': 'HADOOP_DATANODE_OPTS=\\"-Xmx%sm\\"'
    },
    "JobFlow": {
        'Oozie Heap Size': 'CATALINA_OPTS -Xmx%sm'
    }
}

ENABLE_SWIFT = p.Config('Enable Swift', 'general', 'cluster',
                        config_type="bool", priority=1,
                        default_value=True, is_optional=True)

ENABLE_DATA_LOCALITY = p.Config('Enable Data Locality', 'general', 'cluster',
                                config_type="bool", priority=1,
                                default_value=True, is_optional=True)

ENABLE_MYSQL = p.Config('Enable MySQL', 'general', 'cluster',
                        config_type="bool", priority=1,
                        default_value=True, is_optional=True)

# Default set to 1 day, which is the default Keystone token
# expiration time. After the token is expired we can't continue
# scaling anyway.
DECOMMISSIONING_TIMEOUT = p.Config('Decommissioning Timeout', 'general',
                                   'cluster', config_type='int', priority=1,
                                   default_value=86400, is_optional=True,
                                   description='Timeout for datanode'
                                               ' decommissioning operation'
                                               ' during scaling, in seconds')


HIDDEN_CONFS = ['fs.default.name', 'dfs.name.dir', 'dfs.data.dir',
                'mapred.job.tracker', 'mapred.system.dir', 'mapred.local.dir',
                'hadoop.proxyuser.hadoop.hosts',
                'hadoop.proxyuser.hadoop.groups']

CLUSTER_WIDE_CONFS = ['dfs.block.size', 'dfs.permissions', 'dfs.replication',
                      'dfs.replication.min', 'dfs.replication.max',
                      'io.file.buffer.size', 'mapreduce.job.counters.max',
                      'mapred.output.compress', 'io.compression.codecs',
                      'mapred.output.compression.codec',
                      'mapred.output.compression.type',
                      'mapred.compress.map.output',
                      'mapred.map.output.compression.codec']

PRIORITY_1_CONFS = ['dfs.datanode.du.reserved',
                    'dfs.datanode.failed.volumes.tolerated',
                    'dfs.datanode.max.xcievers', 'dfs.datanode.handler.count',
                    'dfs.namenode.handler.count', 'mapred.child.java.opts',
                    'mapred.jobtracker.maxtasks.per.job',
                    'mapred.job.tracker.handler.count',
                    'mapred.map.child.java.opts',
                    'mapred.reduce.child.java.opts',
                    'io.sort.mb', 'mapred.tasktracker.map.tasks.maximum',
                    'mapred.tasktracker.reduce.tasks.maximum']

# for now we have not so many cluster-wide configs
# lets consider all of them having high priority
PRIORITY_1_CONFS += CLUSTER_WIDE_CONFS


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
                    elif types.is_int(cfg.default_value):
                        cfg.config_type = "int"
                        cfg.default_value = int(cfg.default_value)
                    if config['name'] in CLUSTER_WIDE_CONFS:
                        cfg.scope = 'cluster'
                    if config['name'] in PRIORITY_1_CONFS:
                        cfg.priority = 1
                    configs.append(cfg)

    for service, config_items in ENV_CONFS.iteritems():
        for name, param_format_str in config_items.iteritems():
            configs.append(p.Config(name, service, "node",
                                    default_value=1024, priority=1,
                                    config_type="int"))

    configs.append(ENABLE_SWIFT)
    configs.append(ENABLE_MYSQL)
    configs.append(DECOMMISSIONING_TIMEOUT)
    if CONF.enable_data_locality:
        configs.append(ENABLE_DATA_LOCALITY)

    return configs

# Initialise plugin Hadoop configurations
PLUGIN_CONFIGS = _initialise_configs()


def get_plugin_configs():
    return PLUGIN_CONFIGS


def get_general_configs(hive_hostname, passwd_hive_mysql):
    config = {
        ENABLE_SWIFT.name: {
            'default_value': ENABLE_SWIFT.default_value,
            'conf': extract_name_values(swift.get_swift_configs())
        },
        ENABLE_MYSQL.name: {
            'default_value': ENABLE_MYSQL.default_value,
            'conf': m_h.get_required_mysql_configs(
                hive_hostname, passwd_hive_mysql)
        }
    }
    if CONF.enable_data_locality:
        config.update({
            ENABLE_DATA_LOCALITY.name: {
                'default_value': ENABLE_DATA_LOCALITY.default_value,
                'conf': extract_name_values(topology.vm_awareness_all_config())
            }
        })
    return config


def get_config_value(service, name, cluster=None):
    if cluster:
        sahara_configs = generate_sahara_configs(cluster)
        if sahara_configs.get(name):
            return sahara_configs[name]

        for ng in cluster.node_groups:
            if (ng.configuration().get(service) and
                    ng.configuration()[service].get(name)):
                return ng.configuration()[service][name]

    for configs in PLUGIN_CONFIGS:
        if configs.applicable_target == service and configs.name == name:
            return configs.default_value

    raise ex.ConfigurationError(_("Unable get parameter '%(parameter)s' from "
                                  "service %(service)s")
                                % {"parameter": name, "service": service})


def generate_cfg_from_general(cfg, configs, general_config,
                              rest_excluded=False):
    if 'general' in configs:
        for nm in general_config:
            if nm not in configs['general'] and not rest_excluded:
                configs['general'][nm] = general_config[nm]['default_value']
        for name, value in configs['general'].items():
            if value:
                cfg = _set_config(cfg, general_config, name)
                LOG.debug("Applying config: {config}".format(config=name))
    else:
        cfg = _set_config(cfg, general_config)
    return cfg


def get_hadoop_ssh_keys(cluster):
    extra = cluster.extra.to_dict() if cluster.extra else {}
    private_key = extra.get('hadoop_private_ssh_key')
    public_key = extra.get('hadoop_public_ssh_key')
    if not private_key or not public_key:
        private_key, public_key = crypto.generate_key_pair()
        extra['hadoop_private_ssh_key'] = private_key
        extra['hadoop_public_ssh_key'] = public_key
        conductor.cluster_update(context.ctx(), cluster, {'extra': extra})

    return private_key, public_key


def generate_sahara_configs(cluster, node_group=None):
    nn_hostname = vu.get_instance_hostname(vu.get_namenode(cluster))
    jt_hostname = vu.get_instance_hostname(vu.get_jobtracker(cluster))
    oozie_hostname = vu.get_instance_hostname(vu.get_oozie(cluster))
    hive_hostname = vu.get_instance_hostname(vu.get_hiveserver(cluster))

    storage_path = node_group.storage_paths() if node_group else None

    # inserting common configs depends on provisioned VMs and HDFS placement
    # TODO(aignatov): should be moved to cluster context

    cfg = {
        'fs.default.name': 'hdfs://%s:8020' % nn_hostname,
        'dfs.name.dir': extract_hadoop_path(storage_path,
                                            '/lib/hadoop/hdfs/namenode'),
        'dfs.data.dir': extract_hadoop_path(storage_path,
                                            '/lib/hadoop/hdfs/datanode'),
        'dfs.hosts': '/etc/hadoop/dn.incl',
        'dfs.hosts.exclude': '/etc/hadoop/dn.excl',
    }

    if jt_hostname:
        mr_cfg = {
            'mapred.job.tracker': '%s:8021' % jt_hostname,
            'mapred.system.dir': extract_hadoop_path(storage_path,
                                                     '/mapred/mapredsystem'),
            'mapred.local.dir': extract_hadoop_path(storage_path,
                                                    '/lib/hadoop/mapred'),
            'mapred.hosts': '/etc/hadoop/tt.incl',
            'mapred.hosts.exclude': '/etc/hadoop/tt.excl',
        }
        cfg.update(mr_cfg)

    if oozie_hostname:
        o_cfg = {
            'hadoop.proxyuser.hadoop.hosts': "localhost," + oozie_hostname,
            'hadoop.proxyuser.hadoop.groups': 'hadoop',
        }
        cfg.update(o_cfg)
        LOG.debug('Applied Oozie configs for core-site.xml')
        cfg.update(o_h.get_oozie_required_xml_configs())
        LOG.debug('Applied Oozie configs for oozie-site.xml')

    if hive_hostname:
        h_cfg = {
            'hive.warehouse.subdir.inherit.perms': True,
            'javax.jdo.option.ConnectionURL':
            'jdbc:derby:;databaseName=/opt/hive/metastore_db;create=true'
        }
        cfg.update(h_cfg)
        LOG.debug('Applied Hive config for hive metastore server')

    return cfg


def generate_xml_configs(cluster, node_group, hive_mysql_passwd):
    oozie_hostname = vu.get_instance_hostname(vu.get_oozie(cluster))
    hive_hostname = vu.get_instance_hostname(vu.get_hiveserver(cluster))

    ng_configs = node_group.configuration()

    general_cfg = get_general_configs(hive_hostname, hive_mysql_passwd)

    all_cfg = generate_sahara_configs(cluster, node_group)

    # inserting user-defined configs
    for key, value in extract_xml_confs(ng_configs):
        all_cfg[key] = value

    # applying swift configs if user enabled it
    swift_xml_confs = swift.get_swift_configs()
    all_cfg = generate_cfg_from_general(all_cfg, ng_configs, general_cfg)

    # invoking applied configs to appropriate xml files
    core_all = CORE_DEFAULT + swift_xml_confs
    mapred_all = MAPRED_DEFAULT

    if CONF.enable_data_locality:
        all_cfg.update(topology.TOPOLOGY_CONFIG)

        # applying vm awareness configs
        core_all += topology.vm_awareness_core_config()
        mapred_all += topology.vm_awareness_mapred_config()

    xml_configs = {
        'core-site': x.create_hadoop_xml(all_cfg, core_all),
        'mapred-site': x.create_hadoop_xml(all_cfg, mapred_all),
        'hdfs-site': x.create_hadoop_xml(all_cfg, HDFS_DEFAULT)
    }

    if hive_hostname:
        cfg = all_cfg
        cfg_filter = HIVE_DEFAULT
        proxy_configs = cluster.cluster_configs.get('proxy_configs')
        if CONF.use_identity_api_v3 and proxy_configs:
            cfg, cfg_filter = _inject_swift_trust_info(cfg,
                                                       cfg_filter,
                                                       proxy_configs)
        xml_configs.update({'hive-site':
                            x.create_hadoop_xml(cfg, cfg_filter)})
        LOG.debug('Generated hive-site.xml for hive {host}'.format(
            host=hive_hostname))

    if oozie_hostname:
        xml_configs.update({'oozie-site':
                            x.create_hadoop_xml(all_cfg, o_h.OOZIE_DEFAULT)})
        LOG.debug('Generated oozie-site.xml for oozie {host}'.format(
            host=oozie_hostname))

    return xml_configs


def _inject_swift_trust_info(cfg, cfg_filter, proxy_configs):
    cfg = cfg.copy()
    cfg.update({
        swift.HADOOP_SWIFT_USERNAME: proxy_configs['proxy_username'],
        swift.HADOOP_SWIFT_PASSWORD: proxy_configs['proxy_password'],
        swift.HADOOP_SWIFT_TRUST_ID: proxy_configs['proxy_trust_id'],
        swift.HADOOP_SWIFT_DOMAIN_NAME: CONF.proxy_user_domain_name
    })

    allow_swift_auth_filter = [
        {'name': swift.HADOOP_SWIFT_USERNAME},
        {'name': swift.HADOOP_SWIFT_PASSWORD},
        {'name': swift.HADOOP_SWIFT_TRUST_ID},
        {'name': swift.HADOOP_SWIFT_DOMAIN_NAME}
    ]
    cfg_filter = cfg_filter + allow_swift_auth_filter

    return cfg, cfg_filter


def extract_environment_confs(configs):
    """Returns environment specific Hadoop configurations.

    :returns list of Hadoop parameters which should be passed via environment
    """

    lst = []
    for service, srv_confs in configs.items():
        if ENV_CONFS.get(service):
            for param_name, param_value in srv_confs.items():
                for cfg_name, cfg_format_str in ENV_CONFS[service].items():
                    if param_name == cfg_name and param_value is not None:
                        lst.append(cfg_format_str % param_value)
        else:
            LOG.warning(_LW("Plugin received wrong applicable target {service}"
                            " in environmental configs").format(
                                service=service))
    return sorted(lst)


def extract_xml_confs(configs):
    """Returns xml specific Hadoop configurations.

    :returns list of Hadoop parameters which should be passed into general
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
            LOG.warning(_LW("Plugin received wrong applicable target {service}"
                            " for xml configs").format(service=service))
    return sorted(lst)


def generate_setup_script(storage_paths, env_configs, append_oozie=False):
    script_lines = ["#!/bin/bash -x"]
    script_lines.append("echo -n > /tmp/hadoop-env.sh")
    for line in env_configs:
        if 'HADOOP' in line:
            script_lines.append('echo "%s" >> /tmp/hadoop-env.sh' % line)
    script_lines.append("cat /etc/hadoop/hadoop-env.sh >> /tmp/hadoop-env.sh")
    script_lines.append("cp /tmp/hadoop-env.sh /etc/hadoop/hadoop-env.sh")

    hadoop_log = storage_paths[0] + "/log/hadoop/\$USER/"
    script_lines.append('sed -i "s,export HADOOP_LOG_DIR=.*,'
                        'export HADOOP_LOG_DIR=%s," /etc/hadoop/hadoop-env.sh'
                        % hadoop_log)

    hadoop_log = storage_paths[0] + "/log/hadoop/hdfs"
    script_lines.append('sed -i "s,export HADOOP_SECURE_DN_LOG_DIR=.*,'
                        'export HADOOP_SECURE_DN_LOG_DIR=%s," '
                        '/etc/hadoop/hadoop-env.sh' % hadoop_log)

    if append_oozie:
        o_h.append_oozie_setup(script_lines, env_configs)

    for path in storage_paths:
        script_lines.append("chown -R hadoop:hadoop %s" % path)
        script_lines.append("chmod -R 755 %s" % path)
    return "\n".join(script_lines)


def extract_name_values(configs):
    return dict((cfg['name'], cfg['value']) for cfg in configs)


def extract_hadoop_path(lst, hadoop_dir):
    if lst:
        return ",".join([p + hadoop_dir for p in lst])


def _set_config(cfg, gen_cfg, name=None):
    if name in gen_cfg:
        cfg.update(gen_cfg[name]['conf'])
    if name is None:
        for name in gen_cfg:
            cfg.update(gen_cfg[name]['conf'])
    return cfg


def _get_general_cluster_config_value(cluster, option):
    conf = cluster.cluster_configs

    if 'general' in conf and option.name in conf['general']:
        return conf['general'][option.name]

    return option.default_value


def is_mysql_enable(cluster):
    return _get_general_cluster_config_value(cluster, ENABLE_MYSQL)


def is_data_locality_enabled(cluster):
    if not CONF.enable_data_locality:
        return False
    return _get_general_cluster_config_value(cluster, ENABLE_DATA_LOCALITY)


def is_swift_enable(cluster):
    return _get_general_cluster_config_value(cluster, ENABLE_SWIFT)


def get_decommissioning_timeout(cluster):
    return _get_general_cluster_config_value(cluster, DECOMMISSIONING_TIMEOUT)


def get_port_from_config(service, name, cluster=None):
    address = get_config_value(service, name, cluster)
    return utils.get_port_from_address(address)
