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


from oslo_serialization import jsonutils
import six

from sahara.i18n import _
from sahara.plugins.ambari import common
from sahara.plugins import provisioning
from sahara.plugins import utils
from sahara.swift import swift_helper
from sahara.utils import files


CONFIGS = {}
OBJ_CONFIGS = {}
CFG_PROCESS_MAP = {
    "admin-properties": common.RANGER_SERVICE,
    "ams-env": common.AMBARI_SERVICE,
    "ams-hbase-env": common.AMBARI_SERVICE,
    "ams-hbase-policy": common.AMBARI_SERVICE,
    "ams-hbase-security-site": common.AMBARI_SERVICE,
    "ams-hbase-site": common.AMBARI_SERVICE,
    "ams-site": common.AMBARI_SERVICE,
    "capacity-scheduler": common.YARN_SERVICE,
    "cluster-env": "general",
    "core-site": common.HDFS_SERVICE,
    "falcon-env": common.FALCON_SERVICE,
    "falcon-runtime.properties": common.FALCON_SERVICE,
    "falcon-startup.properties": common.FALCON_SERVICE,
    "flume-env": common.FLUME_SERVICE,
    "gateway-site": common.KNOX_SERVICE,
    "hadoop-env": common.HDFS_SERVICE,
    "hadoop-policy": common.HDFS_SERVICE,
    "hbase-env": common.HBASE_SERVICE,
    "hbase-policy": common.HBASE_SERVICE,
    "hbase-site": common.HBASE_SERVICE,
    "hdfs-site": common.HDFS_SERVICE,
    "hive-env": common.HIVE_SERVICE,
    "hive-site": common.HIVE_SERVICE,
    "hiveserver2-site": common.HIVE_SERVICE,
    "kafka-broker": common.KAFKA_SERVICE,
    "kafka-env": common.KAFKA_SERVICE,
    "knox-env": common.KNOX_SERVICE,
    "mapred-env": common.YARN_SERVICE,
    "mapred-site": common.YARN_SERVICE,
    "oozie-env": common.OOZIE_SERVICE,
    "oozie-site": common.OOZIE_SERVICE,
    "ranger-env": common.RANGER_SERVICE,
    "ranger-hbase-plugin-properties": common.HBASE_SERVICE,
    "ranger-hdfs-plugin-properties": common.HDFS_SERVICE,
    "ranger-hive-plugin-properties": common.HIVE_SERVICE,
    "ranger-knox-plugin-properties": common.KNOX_SERVICE,
    "ranger-site": common.RANGER_SERVICE,
    "ranger-storm-plugin-properties": common.STORM_SERVICE,
    "spark-defaults": common.SPARK_SERVICE,
    "spark-env": common.SPARK_SERVICE,
    "sqoop-env": common.SQOOP_SERVICE,
    "storm-env": common.STORM_SERVICE,
    "storm-site": common.STORM_SERVICE,
    "tez-site": common.OOZIE_SERVICE,
    "usersync-properties": common.RANGER_SERVICE,
    "yarn-env": common.YARN_SERVICE,
    "yarn-site": common.YARN_SERVICE,
    "zoo.cfg": common.ZOOKEEPER_SERVICE,
    "zookeeper-env": common.ZOOKEEPER_SERVICE
}


SERVICES_TO_CONFIGS_MAP = None


def get_service_to_configs_map():
    global SERVICES_TO_CONFIGS_MAP
    if SERVICES_TO_CONFIGS_MAP:
        return SERVICES_TO_CONFIGS_MAP
    data = {}
    for (key, item) in six.iteritems(CFG_PROCESS_MAP):
        if item not in data:
            data[item] = []
        data[item].append(key)
    SERVICES_TO_CONFIGS_MAP = data
    return SERVICES_TO_CONFIGS_MAP


ng_confs = [
    "dfs.datanode.data.dir",
    "dtnode_heapsize",
    "mapreduce.map.java.opts",
    "mapreduce.map.memory.mb",
    "mapreduce.reduce.java.opts",
    "mapreduce.reduce.memory.mb",
    "mapreduce.task.io.sort.mb",
    "nodemanager_heapsize",
    "yarn.app.mapreduce.am.command-opts",
    "yarn.app.mapreduce.am.resource.mb",
    "yarn.nodemanager.resource.cpu-vcores",
    "yarn.nodemanager.resource.memory-mb",
    "yarn.scheduler.maximum-allocation-mb",
    "yarn.scheduler.minimum-allocation-mb"
]


use_base_repos_cfg = provisioning.Config(
    "Enable external repos on instances", 'general', 'cluster', priority=1,
    default_value=True, config_type="bool")
hdp_repo_cfg = provisioning.Config(
    "HDP repo URL", "general", "cluster", priority=1, default_value="")
hdp_utils_repo_cfg = provisioning.Config(
    "HDP-UTILS repo URL", "general", "cluster", priority=1, default_value="")


def _get_service_name(service):
    return CFG_PROCESS_MAP.get(service, service)


def _get_config_group(group, param, plugin_version):
    if not CONFIGS or plugin_version not in CONFIGS:
        load_configs(plugin_version)
    for section, process in six.iteritems(CFG_PROCESS_MAP):
        if process == group and param in CONFIGS[plugin_version][section]:
            return section


def _get_param_scope(param):
    if param in ng_confs:
        return "node"
    else:
        return "cluster"


def _get_ha_params():
    enable_namenode_ha = provisioning.Config(
        name=common.NAMENODE_HA,
        applicable_target="general",
        scope="cluster",
        config_type="bool",
        default_value=False,
        is_optional=True,
        description=_("Enable NameNode HA"),
        priority=1)

    enable_resourcemanager_ha = provisioning.Config(
        name=common.RESOURCEMANAGER_HA,
        applicable_target="general",
        scope="cluster",
        config_type="bool",
        default_value=False,
        is_optional=True,
        description=_("Enable ResourceManager HA"),
        priority=1)

    enable_regionserver_ha = provisioning.Config(
        name=common.HBASE_REGIONSERVER_HA,
        applicable_target="general",
        scope="cluster",
        config_type="bool",
        default_value=False,
        is_optional=True,
        description=_("Enable HBase RegionServer HA"),
        priority=1)

    return [enable_namenode_ha,
            enable_resourcemanager_ha,
            enable_regionserver_ha]


def load_configs(version):
    if OBJ_CONFIGS.get(version):
        return OBJ_CONFIGS[version]
    cfg_path = "plugins/ambari/resources/configs-%s.json" % version
    vanilla_cfg = jsonutils.loads(files.get_file_text(cfg_path))
    CONFIGS[version] = vanilla_cfg
    sahara_cfg = [hdp_repo_cfg, hdp_utils_repo_cfg, use_base_repos_cfg]
    for service, confs in vanilla_cfg.items():
        for k, v in confs.items():
            sahara_cfg.append(provisioning.Config(
                k, _get_service_name(service), _get_param_scope(k),
                default_value=v))

    sahara_cfg.extend(_get_ha_params())
    OBJ_CONFIGS[version] = sahara_cfg
    return sahara_cfg


def _get_config_value(cluster, key):
    return cluster.cluster_configs.get("general", {}).get(key.name,
                                                          key.default_value)


def use_base_repos_needed(cluster):
    return _get_config_value(cluster, use_base_repos_cfg)


def get_hdp_repo_url(cluster):
    return _get_config_value(cluster, hdp_repo_cfg)


def get_hdp_utils_repo_url(cluster):
    return _get_config_value(cluster, hdp_utils_repo_cfg)


def _serialize_ambari_configs(configs):
    return list(map(lambda x: {x: configs[x]}, configs))


def _create_ambari_configs(sahara_configs, plugin_version):
    configs = {}
    for service, params in six.iteritems(sahara_configs):
        if service == "general":
            # General configs are designed for Sahara, not for the plugin
            continue
        for k, v in six.iteritems(params):
            group = _get_config_group(service, k, plugin_version)
            configs.setdefault(group, {})
            configs[group].update({k: v})
    return configs


def _make_paths(dirs, suffix):
    return ",".join([d + suffix for d in dirs])


def get_instance_params_mapping(inst):
    configs = _create_ambari_configs(inst.node_group.node_configs,
                                     inst.node_group.cluster.hadoop_version)
    storage_paths = inst.storage_paths()
    configs.setdefault("hdfs-site", {})
    configs["hdfs-site"]["dfs.datanode.data.dir"] = _make_paths(
        storage_paths, "/hdfs/data")
    configs["hdfs-site"]["dfs.journalnode.edits.dir"] = _make_paths(
        storage_paths, "/hdfs/journalnode")
    configs["hdfs-site"]["dfs.namenode.checkpoint.dir"] = _make_paths(
        storage_paths, "/hdfs/namesecondary")
    configs["hdfs-site"]["dfs.namenode.name.dir"] = _make_paths(
        storage_paths, "/hdfs/namenode")
    configs.setdefault("yarn-site", {})
    configs["yarn-site"]["yarn.nodemanager.local-dirs"] = _make_paths(
        storage_paths, "/yarn/local")
    configs["yarn-site"]["yarn.nodemanager.log-dirs"] = _make_paths(
        storage_paths, "/yarn/log")
    configs["yarn-site"][
        "yarn.timeline-service.leveldb-timeline-store.path"] = _make_paths(
            storage_paths, "/yarn/timeline")
    configs.setdefault("oozie-site", {})
    configs["oozie-site"][
        "oozie.service.AuthorizationService.security.enabled"] = "false"
    return configs


def get_instance_params(inst):
    return _serialize_ambari_configs(get_instance_params_mapping(inst))


def get_cluster_params(cluster):
    configs = _create_ambari_configs(cluster.cluster_configs,
                                     cluster.hadoop_version)
    swift_configs = {x["name"]: x["value"]
                     for x in swift_helper.get_swift_configs()}
    configs.setdefault("core-site", {})
    configs["core-site"].update(swift_configs)
    if utils.get_instance(cluster, common.RANGER_ADMIN):
        configs.setdefault("admin-properties", {})
        configs["admin-properties"]["db_root_password"] = (
            cluster.extra["ranger_db_password"])
    return _serialize_ambari_configs(configs)


def get_config_group(instance):
    params = get_instance_params_mapping(instance)
    groups = []
    for (service, targets) in six.iteritems(get_service_to_configs_map()):
        current_group = {
            'cluster_name': instance.cluster.name,
            'group_name': "%s:%s" % (
                instance.cluster.name, instance.instance_name),
            'tag': service,
            'description': "Config group for scaled "
                           "node %s" % instance.instance_name,
            'hosts': [
                {
                    'host_name': instance.fqdn()
                }
            ],
            'desired_configs': []
        }
        at_least_one_added = False
        for target in targets:
            configs = params.get(target, {})
            if configs:
                current_group['desired_configs'].append({
                    'type': target,
                    'properties': configs,
                    'tag': instance.instance_name
                })
                at_least_one_added = True
        if at_least_one_added:
            # Config Group without overridden data is not interesting
            groups.append({'ConfigGroup': current_group})
    return groups
