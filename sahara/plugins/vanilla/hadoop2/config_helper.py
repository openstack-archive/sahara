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

from oslo_config import cfg
import six

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.plugins import provisioning as p
from sahara.plugins import utils
from sahara.utils import files as f
from sahara.utils import types

CONF = cfg.CONF
CONF.import_opt("enable_data_locality", "sahara.topology.topology_helper")


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

_default_executor_classpath = ":".join(
    ['/opt/hadoop/share/hadoop/tools/lib/hadoop-openstack-2.7.1.jar'])

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

# for now we have not so many cluster-wide configs
# lets consider all of them having high priority
PRIORITY_1_CONFS += CLUSTER_WIDE_CONFS


def init_xml_configs(xml_confs):
    configs = []
    for service, config_lists in six.iteritems(xml_confs):
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


ENABLE_SWIFT = p.Config('Enable Swift', 'general', 'cluster',
                        config_type="bool", priority=1,
                        default_value=True, is_optional=False)

ENABLE_MYSQL = p.Config('Enable MySQL', 'general', 'cluster',
                        config_type="bool", priority=1,
                        default_value=True, is_optional=True)

ENABLE_DATA_LOCALITY = p.Config('Enable Data Locality', 'general', 'cluster',
                                config_type="bool", priority=1,
                                default_value=True, is_optional=True)


DATANODES_DECOMMISSIONING_TIMEOUT = p.Config(
    'DataNodes decommissioning timeout', 'general',
    'cluster', config_type='int', priority=1,
    default_value=3600 * 4, is_optional=True,
    description='Timeout for datanode decommissioning operation'
                ' during scaling, in seconds')


NODEMANAGERS_DECOMMISSIONING_TIMEOUT = p.Config(
    'NodeManagers decommissioning timeout', 'general',
    'cluster', config_type='int', priority=1,
    default_value=300, is_optional=True,
    description='Timeout for NodeManager decommissioning operation'
                ' during scaling, in seconds')


DATANODES_STARTUP_TIMEOUT = p.Config(
    'DataNodes startup timeout', 'general', 'cluster', config_type='int',
    priority=1, default_value=10800, is_optional=True,
    description='Timeout for DataNodes startup, in seconds')


def init_env_configs(env_confs):
    configs = []
    for service, config_items in six.iteritems(env_confs):
        for name, value in six.iteritems(config_items):
            configs.append(p.Config(name, service, "node",
                                    default_value=value, priority=1,
                                    config_type="int"))

    return configs


def _init_general_configs():
    configs = [ENABLE_SWIFT, ENABLE_MYSQL, DATANODES_STARTUP_TIMEOUT,
               DATANODES_DECOMMISSIONING_TIMEOUT,
               NODEMANAGERS_DECOMMISSIONING_TIMEOUT]
    if CONF.enable_data_locality:
        configs.append(ENABLE_DATA_LOCALITY)
    return configs

PLUGIN_GENERAL_CONFIGS = _init_general_configs()


def get_config_value(pctx, service, name, cluster=None):
    if cluster:
        for ng in cluster.node_groups:
            cl_param = ng.configuration().get(service, {}).get(name)
            if cl_param is not None:
                return cl_param

    for c in pctx['all_confs']:
        if c.applicable_target == service and c.name == name:
            return c.default_value

    raise ex.NotFoundException(
        {"name": name, "service": service},
        _("Unable to get parameter '%(name)s' from service %(service)s"))


def is_swift_enabled(pctx, cluster):
    return get_config_value(pctx, ENABLE_SWIFT.applicable_target,
                            ENABLE_SWIFT.name, cluster)


def is_mysql_enabled(pctx, cluster):
    return get_config_value(
        pctx, ENABLE_MYSQL.applicable_target, ENABLE_MYSQL.name, cluster)


def is_data_locality_enabled(pctx, cluster):
    if not CONF.enable_data_locality:
        return False
    return get_config_value(pctx, ENABLE_DATA_LOCALITY.applicable_target,
                            ENABLE_DATA_LOCALITY.name, cluster)


def _get_spark_opt_default(opt_name):
    for opt in SPARK_CONFS["Spark"]["OPTIONS"]:
        if opt_name == opt["name"]:
            return opt["default"]
    return None


def generate_spark_env_configs(cluster):
    configs = []

    # point to the hadoop conf dir so that Spark can read things
    # like the swift configuration without having to copy core-site
    # to /opt/spark/conf
    HADOOP_CONF_DIR = '/opt/hadoop/etc/hadoop'
    configs.append('HADOOP_CONF_DIR=' + HADOOP_CONF_DIR)

    # Hadoop and YARN configs there are in one folder
    configs.append('YARN_CONF_DIR=' + HADOOP_CONF_DIR)

    return '\n'.join(configs)


def generate_spark_executor_classpath(cluster):
    cp = utils.get_config_value_or_default(
        "Spark", "Executor extra classpath", cluster)
    if cp:
        return "spark.executor.extraClassPath " + cp
    return "\n"


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
            'plugins/vanilla/hadoop2/resources/spark-cleanup.cron'),
        job_cleanup_script = f.get_file_text(
            'plugins/vanilla/hadoop2/resources/tmp-cleanup.sh.template')
        job_conf['script'] = job_cleanup_script.format(**args)
    return job_conf


def get_spark_home(cluster):
    return utils.get_config_value_or_default("Spark", "Spark home", cluster)
