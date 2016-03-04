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

from sahara.plugins.ambari import common as p_common
from sahara.plugins import utils


CORE_SITE = "core-site"
YARN_SITE = "yarn-site"
HBASE_SITE = "hbase-site"
HDFS_SITE = "hdfs-site"
HADOOP_ENV = "hadoop-env"
ZOO_CFG = "zoo.cfg"


def update_bp_ha_common(cluster, blueprint):
    blueprint = _set_default_fs(cluster, blueprint, p_common.NAMENODE_HA)
    blueprint = _set_high_zk_limits(blueprint)

    return blueprint


def update_bp_for_namenode_ha(cluster, blueprint):
    blueprint = _add_zkfc_to_namenodes(blueprint)
    blueprint = _set_zk_quorum(cluster, blueprint, CORE_SITE)
    blueprint = _configure_hdfs_site(cluster, blueprint)

    return blueprint


def update_bp_for_resourcemanager_ha(cluster, blueprint):
    blueprint = _configure_yarn_site(cluster, blueprint)
    blueprint = _set_zk_quorum(cluster, blueprint, YARN_SITE)
    blueprint = _set_default_fs(cluster, blueprint,
                                p_common.RESOURCEMANAGER_HA)
    return blueprint


def update_bp_for_hbase_ha(cluster, blueprint):
    return _confgure_hbase_site(cluster, blueprint)


def _add_zkfc_to_namenodes(blueprint):
    for hg in blueprint["host_groups"]:
        if {"name": "NAMENODE"} in hg["components"]:
            hg["components"].append({"name": "ZKFC"})

    return blueprint


def _find_create_properties_section(blueprint, section_name):
    for conf_group in blueprint["configurations"]:
        if section_name in conf_group:
            return conf_group[section_name]

    new_group = {section_name: {}}
    blueprint["configurations"].append(new_group)

    return new_group[section_name]


def _find_hdfs_site(blueprint):
    return _find_create_properties_section(blueprint, HDFS_SITE)


def _find_yarn_site(blueprint):
    return _find_create_properties_section(blueprint, YARN_SITE)


def _find_core_site(blueprint):
    return _find_create_properties_section(blueprint, CORE_SITE)


def _find_hadoop_env(blueprint):
    return _find_create_properties_section(blueprint, HADOOP_ENV)


def _find_zoo_cfg(blueprint):
    return _find_create_properties_section(blueprint, ZOO_CFG)


def _find_hbase_site(blueprint):
    return _find_create_properties_section(blueprint, HBASE_SITE)


def _set_default_fs(cluster, blueprint, ha_type):
    if ha_type == p_common.NAMENODE_HA:
        _find_core_site(blueprint)["fs.defaultFS"] = "hdfs://hdfs-ha"
    elif ha_type == p_common.RESOURCEMANAGER_HA:
        nn_instance = utils.get_instances(cluster, p_common.NAMENODE)[0]
        _find_core_site(blueprint)["fs.defaultFS"] = (
            "hdfs://%s:8020" % nn_instance.fqdn())
    return blueprint


def _set_zk_quorum(cluster, blueprint, conf_type):
    zk_instances = utils.get_instances(cluster, p_common.ZOOKEEPER_SERVER)

    value = ",".join(["%s:2181" % i.fqdn() for i in zk_instances])
    if conf_type == CORE_SITE:
        _find_core_site(blueprint)["ha.zookeeper.quorum"] = value
    elif conf_type == YARN_SITE:
        _find_yarn_site(blueprint)["hadoop.registry.zk.quorum"] = value

    return blueprint


def _set_high_zk_limits(blueprint):
    props = _find_zoo_cfg(blueprint)
    props["tickTime"] = "10000"

    return blueprint


def _set_primary_and_standby_namenode(cluster, blueprint):
    props = _find_hadoop_env(blueprint)
    nns = utils.get_instances(cluster, p_common.NAMENODE)
    props["dfs_ha_initial_namenode_active"] = nns[0].fqdn()
    props["dfs_ha_initial_namenode_standby"] = nns[1].fqdn()

    return blueprint


def _configure_hdfs_site(cluster, blueprint):
    props = _find_hdfs_site(blueprint)

    props["dfs.client.failover.proxy.provider.hdfs-ha"] = (
        "org.apache.hadoop.hdfs.server.namenode.ha."
        "ConfiguredFailoverProxyProvider")
    props["dfs.ha.automatic-failover.enabled"] = "true"
    props["dfs.ha.fencing.methods"] = "shell(/bin/true)"
    props["dfs.nameservices"] = "hdfs-ha"

    jns = utils.get_instances(cluster, p_common.JOURNAL_NODE)
    journalnodes_concat = ";".join(
        ["%s:8485" % i.fqdn() for i in jns])
    journalnodes_value = "qjournal://%s/hdfs-ha" % journalnodes_concat
    props["dfs.namenode.shared.edits.dir"] = journalnodes_value

    nns = utils.get_instances(cluster, p_common.NAMENODE)
    nn_id_concat = ",".join([i.instance_name for i in nns])
    props["dfs.ha.namenodes.hdfs-ha"] = nn_id_concat

    props["dfs.namenode.http-address"] = "%s:50070" % nns[0].fqdn()
    props["dfs.namenode.https-address"] = "%s:50470" % nns[0].fqdn()
    for i in nns:
        props["dfs.namenode.http-address.hdfs-ha.%s" % i.instance_name] = (
            "%s:50070" % i.fqdn())
        props["dfs.namenode.https-address.hdfs-ha.%s" % i.instance_name] = (
            "%s:50470" % i.fqdn())
        props["dfs.namenode.rpc-address.hdfs-ha.%s" % i.instance_name] = (
            "%s:8020" % i.fqdn())

    return blueprint


def _configure_yarn_site(cluster, blueprint):
    props = _find_yarn_site(blueprint)
    name = cluster.name
    rm_instances = utils.get_instances(cluster, p_common.RESOURCEMANAGER)

    props["hadoop.registry.rm.enabled"] = "false"

    zk_instances = utils.get_instances(cluster, p_common.ZOOKEEPER_SERVER)

    zks = ",".join(["%s:2181" % i.fqdn() for i in zk_instances])
    props["yarn.resourcemanager.zk-address"] = zks

    hs = utils.get_instance(cluster, p_common.HISTORYSERVER)
    props["yarn.log.server.url"] = "%s:19888/jobhistory/logs/" % hs.fqdn()

    props["yarn.resourcemanager.address"] = "%s:8050" % rm_instances[0].fqdn()
    props["yarn.resourcemanager.admin.address"] = ("%s:8141" %
                                                   rm_instances[0].fqdn())
    props["yarn.resourcemanager.cluster-id"] = name
    props["yarn.resourcemanager.ha.automatic-failover.zk-base-path"] = (
        "/yarn-leader-election")
    props["yarn.resourcemanager.ha.enabled"] = "true"

    rm_id_concat = ",".join([i.instance_name for i in rm_instances])
    props["yarn.resourcemanager.ha.rm-ids"] = rm_id_concat

    for i in rm_instances:
        props["yarn.resourcemanager.hostname.%s" % i.instance_name] = i.fqdn()
        props["yarn.resourcemanager.webapp.address.%s" %
              i.instance_name] = "%s:8088" % i.fqdn()
        props["yarn.resourcemanager.webapp.https.address.%s" %
              i.instance_name] = "%s:8090" % i.fqdn()

    props["yarn.resourcemanager.hostname"] = rm_instances[0].fqdn()
    props["yarn.resourcemanager.recovery.enabled"] = "true"
    props["yarn.resourcemanager.resource-tracker.address"] = (
        "%s:8025" % rm_instances[0].fqdn())
    props["yarn.resourcemanager.scheduler.address"] = (
        "%s:8030" % rm_instances[0].fqdn())
    props["yarn.resourcemanager.store.class"] = (
        "org.apache.hadoop.yarn.server.resourcemanager.recovery."
        "ZKRMStateStore")
    props["yarn.resourcemanager.webapp.address"] = (
        "%s:8088" % rm_instances[0].fqdn())
    props["yarn.resourcemanager.webapp.https.address"] = (
        "%s:8090" % rm_instances[0].fqdn())

    tls_instance = utils.get_instance(cluster, p_common.APP_TIMELINE_SERVER)
    props["yarn.timeline-service.address"] = "%s:10200" % tls_instance.fqdn()
    props["yarn.timeline-service.webapp.address"] = (
        "%s:8188" % tls_instance.fqdn())
    props["yarn.timeline-service.webapp.https.address"] = (
        "%s:8190" % tls_instance.fqdn())

    return blueprint


def _confgure_hbase_site(cluster, blueprint):
    props = _find_hbase_site(blueprint)

    props["hbase.regionserver.global.memstore.lowerLimit"] = "0.38"
    props["hbase.regionserver.global.memstore.upperLimit"] = "0.4"
    props["hbase.regionserver.handler.count"] = "60"
    props["hbase.regionserver.info.port"] = "60030"
    props["hbase.regionserver.storefile.refresh.period"] = "20"

    props["hbase.rootdir"] = "hdfs://hdfs-ha/apps/hbase/data"

    props["hbase.security.authentication"] = "simple"
    props["hbase.security.authorization"] = "false"
    props["hbase.superuser"] = "hbase"
    props["hbase.tmp.dir"] = "/hadoop/hbase"
    props["hbase.zookeeper.property.clientPort"] = "2181"

    zk_instances = utils.get_instances(cluster, p_common.ZOOKEEPER_SERVER)
    zk_quorum_value = ",".join([i.fqdn() for i in zk_instances])
    props["hbase.zookeeper.quorum"] = zk_quorum_value

    props["hbase.zookeeper.useMulti"] = "true"
    props["hfile.block.cache.size"] = "0.40"
    props["zookeeper.session.timeout"] = "30000"
    props["zookeeper.znode.parent"] = "/hbase-unsecure"

    return blueprint
