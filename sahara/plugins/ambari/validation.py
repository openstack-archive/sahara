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


from sahara import conductor
from sahara import context
from sahara.i18n import _
from sahara.plugins.ambari import common
from sahara.plugins import exceptions as ex
from sahara.plugins import utils


conductor = conductor.API


def validate(cluster_id):
    ctx = context.ctx()
    cluster = conductor.cluster_get(ctx, cluster_id)
    _check_ambari(cluster)
    _check_hdfs(cluster)
    _check_yarn(cluster)
    _check_oozie(cluster)
    _check_hive(cluster)
    _check_hbase(cluster)
    _check_spark(cluster)
    _check_ranger(cluster)
    _check_storm(cluster)


def _check_ambari(cluster):
    am_count = utils.get_instances_count(cluster, common.AMBARI_SERVER)
    zk_count = utils.get_instances_count(cluster, common.ZOOKEEPER_SERVER)
    if am_count != 1:
        raise ex.InvalidComponentCountException(common.AMBARI_SERVER, 1,
                                                am_count)
    if zk_count == 0:
        raise ex.InvalidComponentCountException(common.ZOOKEEPER_SERVER,
                                                _("1 or more"), zk_count)


def _check_hdfs(cluster):
    nn_count = utils.get_instances_count(cluster, common.NAMENODE)
    dn_count = utils.get_instances_count(cluster, common.DATANODE)

    if cluster.cluster_configs.get("general", {}).get("NameNode_HA"):
        _check_zk_ha(cluster)
        _check_jn_ha(cluster)

        if nn_count != 2:
            raise ex.InvalidComponentCountException(common.NAMENODE, 2,
                                                    nn_count)
    else:
        if nn_count != 1:
            raise ex.InvalidComponentCountException(common.NAMENODE, 1,
                                                    nn_count)
    if dn_count == 0:
        raise ex.InvalidComponentCountException(
            common.DATANODE, _("1 or more"), dn_count)


def _check_yarn(cluster):
    rm_count = utils.get_instances_count(cluster, common.RESOURCEMANAGER)
    nm_count = utils.get_instances_count(cluster, common.NODEMANAGER)
    hs_count = utils.get_instances_count(cluster, common.HISTORYSERVER)
    at_count = utils.get_instances_count(cluster, common.APP_TIMELINE_SERVER)

    if cluster.cluster_configs.get("general", {}).get("ResourceManager_HA"):
        _check_zk_ha(cluster)

        if rm_count != 2:
            raise ex.InvalidComponentCountException(common.RESOURCEMANAGER, 2,
                                                    rm_count)
    else:
        if rm_count != 1:
            raise ex.InvalidComponentCountException(common.RESOURCEMANAGER, 1,
                                                    rm_count)

    if hs_count != 1:
        raise ex.InvalidComponentCountException(common.HISTORYSERVER, 1,
                                                hs_count)
    if at_count != 1:
        raise ex.InvalidComponentCountException(common.APP_TIMELINE_SERVER, 1,
                                                at_count)
    if nm_count == 0:
        raise ex.InvalidComponentCountException(common.NODEMANAGER,
                                                _("1 or more"), nm_count)


def _check_zk_ha(cluster):
    zk_count = utils.get_instances_count(cluster, common.ZOOKEEPER_SERVER)
    if zk_count < 3:
        raise ex.InvalidComponentCountException(
            common.ZOOKEEPER_SERVER,
            _("3 or more. Odd number"),
            zk_count, _("At least 3 ZooKeepers are required for HA"))
    if zk_count % 2 != 1:
        raise ex.InvalidComponentCountException(
            common.ZOOKEEPER_SERVER,
            _("Odd number"),
            zk_count, _("Odd number of ZooKeepers are required for HA"))


def _check_jn_ha(cluster):
    jn_count = utils.get_instances_count(cluster, common.JOURNAL_NODE)
    if jn_count < 3:
        raise ex.InvalidComponentCountException(
            common.JOURNAL_NODE,
            _("3 or more. Odd number"),
            jn_count, _("At least 3 JournalNodes are required for HA"))
    if jn_count % 2 != 1:
        raise ex.InvalidComponentCountException(
            common.JOURNAL_NODE,
            _("Odd number"),
            jn_count, _("Odd number of JournalNodes are required for HA"))


def _check_oozie(cluster):
    count = utils.get_instances_count(cluster, common.OOZIE_SERVER)
    if count > 1:
        raise ex.InvalidComponentCountException(common.OOZIE_SERVER,
                                                _("0 or 1"), count)


def _check_hive(cluster):
    hs_count = utils.get_instances_count(cluster, common.HIVE_SERVER)
    hm_count = utils.get_instances_count(cluster, common.HIVE_METASTORE)
    if hs_count > 1:
        raise ex.InvalidComponentCountException(common.HIVE_SERVER,
                                                _("0 or 1"), hs_count)
    if hm_count > 1:
        raise ex.InvalidComponentCountException(common.HIVE_METASTORE,
                                                _("0 or 1"), hm_count)
    if hs_count == 0 and hm_count == 1:
        raise ex.RequiredServiceMissingException(
            common.HIVE_SERVER, required_by=common.HIVE_METASTORE)
    if hs_count == 1 and hm_count == 0:
        raise ex.RequiredServiceMissingException(
            common.HIVE_METASTORE, required_by=common.HIVE_SERVER)


def _check_hbase(cluster):
    hm_count = utils.get_instances_count(cluster, common.HBASE_MASTER)
    hr_count = utils.get_instances_count(cluster, common.HBASE_REGIONSERVER)
    if hm_count > 1:
        raise ex.InvalidComponentCountException(common.HBASE_MASTER,
                                                _("0 or 1"), hm_count)
    if hm_count == 1 and hr_count == 0:
        raise ex.RequiredServiceMissingException(
            common.HBASE_REGIONSERVER, required_by=common.HBASE_MASTER)
    if hr_count > 0 and hm_count == 0:
        raise ex.RequiredServiceMissingException(
            common.HBASE_MASTER, required_by=common.HBASE_REGIONSERVER)


def _check_spark(cluster):
    count = utils.get_instances_count(cluster, common.SPARK_JOBHISTORYSERVER)
    if count > 1:
        raise ex.InvalidComponentCountException(common.SPARK_JOBHISTORYSERVER,
                                                _("0 or 1"), count)


def _check_ranger(cluster):
    ra_count = utils.get_instances_count(cluster, common.RANGER_ADMIN)
    ru_count = utils.get_instances_count(cluster, common.RANGER_USERSYNC)
    if ra_count > 1:
        raise ex.InvalidComponentCountException(common.RANGER_ADMIN,
                                                _("0 or 1"), ra_count)
    if ru_count > 1:
        raise ex.InvalidComponentCountException(common.RANGER_USERSYNC,
                                                _("0 or 1"), ru_count)
    if ra_count == 1 and ru_count == 0:
        raise ex.RequiredServiceMissingException(
            common.RANGER_USERSYNC, required_by=common.RANGER_ADMIN)
    if ra_count == 0 and ru_count == 1:
        raise ex.RequiredServiceMissingException(
            common.RANGER_ADMIN, required_by=common.RANGER_USERSYNC)


def _check_storm(cluster):
    dr_count = utils.get_instances_count(cluster, common.DRPC_SERVER)
    ni_count = utils.get_instances_count(cluster, common.NIMBUS)
    su_count = utils.get_instances_count(cluster, common.STORM_UI_SERVER)
    sv_count = utils.get_instances_count(cluster, common.SUPERVISOR)
    if dr_count > 1:
        raise ex.InvalidComponentCountException(common.DRPC_SERVER,
                                                _("0 or 1"), dr_count)
    if ni_count > 1:
        raise ex.InvalidComponentCountException(common.NIMBUS,
                                                _("0 or 1"), ni_count)
    if su_count > 1:
        raise ex.InvalidComponentCountException(common.STORM_UI_SERVER,
                                                _("0 or 1"), su_count)
    if dr_count == 0 and ni_count == 1:
        raise ex.RequiredServiceMissingException(
            common.DRPC_SERVER, required_by=common.NIMBUS)
    if dr_count == 1 and ni_count == 0:
        raise ex.RequiredServiceMissingException(
            common.NIMBUS, required_by=common.DRPC_SERVER)
    if su_count == 1 and (dr_count == 0 or ni_count == 0):
        raise ex.RequiredServiceMissingException(
            common.NIMBUS, required_by=common.STORM_UI_SERVER)
    if dr_count == 1 and sv_count == 0:
        raise ex.RequiredServiceMissingException(
            common.SUPERVISOR, required_by=common.DRPC_SERVER)
    if sv_count > 0 and dr_count == 0:
        raise ex.RequiredServiceMissingException(
            common.DRPC_SERVER, required_by=common.SUPERVISOR)
