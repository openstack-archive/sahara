# Copyright (c) 2014 Hoang Do, Phuc Vo, P. Michiardi, D. Venzano
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

from sahara import conductor as c
from sahara.plugins import provisioning as p
from sahara.plugins import utils
from sahara.swift import swift_helper as swift
from sahara.topology import topology_helper as topology
from sahara.utils import files as f
from sahara.utils import types as types
from sahara.utils import xmlutils as x


conductor = c.API
LOG = logging.getLogger(__name__)
CONF = cfg.CONF

CORE_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/spark/resources/core-default.xml')

HDFS_DEFAULT = x.load_hadoop_xml_defaults(
    'plugins/spark/resources/hdfs-default.xml')

SWIFT_DEFAULTS = swift.read_default_swift_configs()

XML_CONFS = {
    "HDFS": [CORE_DEFAULT, HDFS_DEFAULT, SWIFT_DEFAULTS]
}

_default_executor_classpath = ":".join(
    ['/usr/lib/hadoop/hadoop-swift.jar'])

SPARK_CONFS = {
    'Spark': {
        "OPTIONS": [
            {
                'name': 'Executor extra classpath',
                'description': 'Value for spark.executor.extraClassPath'
                ' in spark-defaults.conf'
                ' (default: %s)' % _default_executor_classpath,
                'default': '%s' % _default_executor_classpath,
                'priority': 2,
            },
            {
                'name': 'Master port',
                'description': 'Start the master on a different port'
                ' (default: 7077)',
                'default': '7077',
                'priority': 2,
            },
            {
                'name': 'Worker port',
                'description': 'Start the Spark worker on a specific port'
                ' (default: random)',
                'default': 'random',
                'priority': 2,
            },
            {
                'name': 'Master webui port',
                'description': 'Port for the master web UI (default: 8080)',
                'default': '8080',
                'priority': 1,
            },
            {
                'name': 'Worker webui port',
                'description': 'Port for the worker web UI (default: 8081)',
                'default': '8081',
                'priority': 1,
            },
            {
                'name': 'Worker cores',
                'description': 'Total number of cores to allow Spark'
                ' applications to use on the machine'
                ' (default: all available cores)',
                'default': 'all',
                'priority': 2,
            },
            {
                'name': 'Worker memory',
                'description': 'Total amount of memory to allow Spark'
                ' applications to use on the machine, e.g. 1000m,'
                ' 2g (default: total memory minus 1 GB)',
                'default': 'all',
                'priority': 1,
            },
            {
                'name': 'Worker instances',
                'description': 'Number of worker instances to run on each'
                ' machine (default: 1)',
                'default': '1',
                'priority': 2,
            },
            {
                'name': 'Spark home',
                'description': 'The location of the spark installation'
                ' (default: /opt/spark)',
                'default': '/opt/spark',
                'priority': 2,
            },
            {
                'name': 'Minimum cleanup seconds',
                'description': 'Job data will never be purged before this'
                ' amount of time elapses (default: 86400 = 1 day)',
                'default': '86400',
                'priority': 2,
            },
            {
                'name': 'Maximum cleanup seconds',
                'description': 'Job data will always be purged after this'
                ' amount of time elapses (default: 1209600 = 14 days)',
                'default': '1209600',
                'priority': 2,
            },
            {
                'name': 'Minimum cleanup megabytes',
                'description': 'No job data will be purged unless the total'
                ' job data exceeds this size (default: 4096 = 4GB)',
                'default': '4096',
                'priority': 2,
            },
        ]
    }
}

HADOOP_CONF_DIR = "/etc/hadoop/conf"

ENV_CONFS = {
    "HDFS": {
        'Name Node Heap Size': 'HADOOP_NAMENODE_OPTS=\\"-Xmx%sm\\"',
        'Data Node Heap Size': 'HADOOP_DATANODE_OPTS=\\"-Xmx%sm\\"'
    }
}

ENABLE_DATA_LOCALITY = p.Config('Enable Data Locality', 'general', 'cluster',
                                config_type="bool", priority=1,
                                default_value=True, is_optional=True)

ENABLE_SWIFT = p.Config('Enable Swift', 'general', 'cluster',
                        config_type="bool", priority=1,
                        default_value=True, is_optional=False)

DATANODES_STARTUP_TIMEOUT = p.Config(
    'DataNodes startup timeout', 'general', 'cluster', config_type='int',
    priority=1, default_value=10800, is_optional=True,
    description='Timeout for DataNodes startup, in seconds')

# Default set to 1 day, which is the default Keystone token
# expiration time. After the token is expired we can't continue
# scaling anyway.
DECOMMISSIONING_TIMEOUT = p.Config('Decommissioning Timeout', 'general',
                                   'cluster', config_type='int', priority=1,
                                   default_value=86400, is_optional=True,
                                   description='Timeout for datanode'
                                               ' decommissioning operation'
                                               ' during scaling, in seconds')

HIDDEN_CONFS = ['fs.defaultFS', 'dfs.namenode.name.dir',
                'dfs.datanode.data.dir']

CLUSTER_WIDE_CONFS = ['dfs.block.size', 'dfs.permissions', 'dfs.replication',
                      'dfs.replication.min', 'dfs.replication.max',
                      'io.file.buffer.size']

PRIORITY_1_CONFS = ['dfs.datanode.du.reserved',
                    'dfs.datanode.failed.volumes.tolerated',
                    'dfs.datanode.max.xcievers', 'dfs.datanode.handler.count',
                    'dfs.namenode.handler.count']

# for now we have not so many cluster-wide configs
# lets consider all of them having high priority
PRIORITY_1_CONFS += CLUSTER_WIDE_CONFS


def _initialise_configs():
    configs = []
    for service, config_lists in six.iteritems(XML_CONFS):
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

    for service, config_items in six.iteritems(ENV_CONFS):
        for name, param_format_str in six.iteritems(config_items):
            configs.append(p.Config(name, service, "node",
                                    default_value=1024, priority=1,
                                    config_type="int"))

    for service, config_items in six.iteritems(SPARK_CONFS):
        for item in config_items['OPTIONS']:
            cfg = p.Config(name=item["name"],
                           description=item["description"],
                           default_value=item["default"],
                           applicable_target=service,
                           scope="cluster", is_optional=True,
                           priority=item["priority"])
            configs.append(cfg)

    configs.append(DECOMMISSIONING_TIMEOUT)
    configs.append(ENABLE_SWIFT)
    configs.append(DATANODES_STARTUP_TIMEOUT)
    if CONF.enable_data_locality:
        configs.append(ENABLE_DATA_LOCALITY)

    return configs

# Initialise plugin Hadoop configurations
PLUGIN_CONFIGS = _initialise_configs()


def get_plugin_configs():
    return PLUGIN_CONFIGS


def generate_cfg_from_general(cfg, configs, general_config,
                              rest_excluded=False):
    if 'general' in configs:
        for nm in general_config:
            if nm not in configs['general'] and not rest_excluded:
                configs['general'][nm] = general_config[nm]['default_value']
        for name, value in configs['general'].items():
            if value:
                cfg = _set_config(cfg, general_config, name)
                LOG.debug("Applying config: {name}".format(name=name))
    else:
        cfg = _set_config(cfg, general_config)
    return cfg


def _get_hostname(service):
    return service.hostname() if service else None


def generate_xml_configs(configs, storage_path, nn_hostname, hadoop_port):
    if hadoop_port is None:
        hadoop_port = 8020

    cfg = {
        'fs.defaultFS': 'hdfs://%s:%s' % (nn_hostname, str(hadoop_port)),
        'dfs.namenode.name.dir': extract_hadoop_path(storage_path,
                                                     '/dfs/nn'),
        'dfs.datanode.data.dir': extract_hadoop_path(storage_path,
                                                     '/dfs/dn'),
        'dfs.hosts': '/etc/hadoop/dn.incl',
        'dfs.hosts.exclude': '/etc/hadoop/dn.excl'
    }

    # inserting user-defined configs
    for key, value in extract_hadoop_xml_confs(configs):
        cfg[key] = value

    # Add the swift defaults if they have not been set by the user
    swft_def = []
    if is_swift_enabled(configs):
        swft_def = SWIFT_DEFAULTS
        swift_configs = extract_name_values(swift.get_swift_configs())
        for key, value in six.iteritems(swift_configs):
            if key not in cfg:
                cfg[key] = value

    # invoking applied configs to appropriate xml files
    core_all = CORE_DEFAULT + swft_def

    if CONF.enable_data_locality:
        cfg.update(topology.TOPOLOGY_CONFIG)
        # applying vm awareness configs
        core_all += topology.vm_awareness_core_config()

    xml_configs = {
        'core-site': x.create_hadoop_xml(cfg, core_all),
        'hdfs-site': x.create_hadoop_xml(cfg, HDFS_DEFAULT)
    }

    return xml_configs


def _get_spark_opt_default(opt_name):
    for opt in SPARK_CONFS["Spark"]["OPTIONS"]:
        if opt_name == opt["name"]:
            return opt["default"]
    return None


def generate_spark_env_configs(cluster):
    configs = []

    # master configuration
    sp_master = utils.get_instance(cluster, "master")
    configs.append('SPARK_MASTER_IP=' + sp_master.hostname())

    # point to the hadoop conf dir so that Spark can read things
    # like the swift configuration without having to copy core-site
    # to /opt/spark/conf
    configs.append('HADOOP_CONF_DIR=' + HADOOP_CONF_DIR)

    masterport = utils.get_config_value_or_default("Spark",
                                                   "Master port",
                                                   cluster)
    if masterport and masterport != _get_spark_opt_default("Master port"):
        configs.append('SPARK_MASTER_PORT=' + str(masterport))

    masterwebport = utils.get_config_value_or_default("Spark",
                                                      "Master webui port",
                                                      cluster)
    if (masterwebport and
            masterwebport != _get_spark_opt_default("Master webui port")):
        configs.append('SPARK_MASTER_WEBUI_PORT=' + str(masterwebport))

    # configuration for workers
    workercores = utils.get_config_value_or_default("Spark",
                                                    "Worker cores",
                                                    cluster)
    if workercores and workercores != _get_spark_opt_default("Worker cores"):
        configs.append('SPARK_WORKER_CORES=' + str(workercores))

    workermemory = utils.get_config_value_or_default("Spark",
                                                     "Worker memory",
                                                     cluster)
    if (workermemory and
            workermemory != _get_spark_opt_default("Worker memory")):
        configs.append('SPARK_WORKER_MEMORY=' + str(workermemory))

    workerport = utils.get_config_value_or_default("Spark",
                                                   "Worker port",
                                                   cluster)
    if workerport and workerport != _get_spark_opt_default("Worker port"):
        configs.append('SPARK_WORKER_PORT=' + str(workerport))

    workerwebport = utils.get_config_value_or_default("Spark",
                                                      "Worker webui port",
                                                      cluster)
    if (workerwebport and
            workerwebport != _get_spark_opt_default("Worker webui port")):
        configs.append('SPARK_WORKER_WEBUI_PORT=' + str(workerwebport))

    workerinstances = utils.get_config_value_or_default("Spark",
                                                        "Worker instances",
                                                        cluster)
    if (workerinstances and
            workerinstances != _get_spark_opt_default("Worker instances")):
        configs.append('SPARK_WORKER_INSTANCES=' + str(workerinstances))
    return '\n'.join(configs)


# workernames need to be a list of woker names
def generate_spark_slaves_configs(workernames):
    return '\n'.join(workernames)


def generate_spark_executor_classpath(cluster):
    cp = utils.get_config_value_or_default("Spark",
                                           "Executor extra classpath",
                                           cluster)
    if cp:
        return "spark.executor.extraClassPath " + cp
    return "\n"


def extract_hadoop_environment_confs(configs):
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
    return lst


def extract_hadoop_xml_confs(configs):
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
    return lst


def generate_hadoop_setup_script(storage_paths, env_configs):
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

    for path in storage_paths:
        script_lines.append("chown -R hadoop:hadoop %s" % path)
        script_lines.append("chmod -f -R 755 %s ||"
                            "echo 'Permissions unchanged'" % path)
    return "\n".join(script_lines)


def generate_job_cleanup_config(cluster):
    args = {
        'minimum_cleanup_megabytes': utils.get_config_value_or_default(
            "Spark", "Minimum cleanup megabytes", cluster),
        'minimum_cleanup_seconds': utils.get_config_value_or_default(
            "Spark", "Minimum cleanup seconds", cluster),
        'maximum_cleanup_seconds': utils.get_config_value_or_default(
            "Spark", "Maximum cleanup seconds", cluster)
    }
    job_conf = {'valid': (args['maximum_cleanup_seconds'] > 0 and
                          (args['minimum_cleanup_megabytes'] > 0
                           and args['minimum_cleanup_seconds'] > 0))}
    if job_conf['valid']:
        job_conf['cron'] = f.get_file_text(
            'plugins/spark/resources/spark-cleanup.cron'),
        job_cleanup_script = f.get_file_text(
            'plugins/spark/resources/tmp-cleanup.sh.template')
        job_conf['script'] = job_cleanup_script.format(**args)
    return job_conf


def extract_name_values(configs):
    return {cfg['name']: cfg['value'] for cfg in configs}


def make_hadoop_path(base_dirs, suffix):
    return [base_dir + suffix for base_dir in base_dirs]


def extract_hadoop_path(lst, hadoop_dir):
    if lst:
        return ",".join(make_hadoop_path(lst, hadoop_dir))


def _set_config(cfg, gen_cfg, name=None):
    if name in gen_cfg:
        cfg.update(gen_cfg[name]['conf'])
    if name is None:
        for name in gen_cfg:
            cfg.update(gen_cfg[name]['conf'])
    return cfg


def _get_general_config_value(conf, option):
    if 'general' in conf and option.name in conf['general']:
        return conf['general'][option.name]
    return option.default_value


def _get_general_cluster_config_value(cluster, option):
    return _get_general_config_value(cluster.cluster_configs, option)


def is_data_locality_enabled(cluster):
    if not CONF.enable_data_locality:
        return False
    return _get_general_cluster_config_value(cluster, ENABLE_DATA_LOCALITY)


def is_swift_enabled(configs):
    return _get_general_config_value(configs, ENABLE_SWIFT)


def get_decommissioning_timeout(cluster):
    return _get_general_cluster_config_value(cluster, DECOMMISSIONING_TIMEOUT)


def get_port_from_config(service, name, cluster=None):
    address = utils.get_config_value_or_default(service, name, cluster)
    return utils.get_port_from_address(address)
