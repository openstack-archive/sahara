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

from sahara.i18n import _
from sahara.plugins import exceptions as ex
from sahara.plugins import utils as u
from sahara.utils import general as gu


class Validator(object):
    PU = None

    @classmethod
    def validate_cluster_creating(cls, cluster):
        cls._basic_validation(cluster)
        cls._oozie_validation(cluster)
        cls._hive_validation(cluster)
        cls._hue_validation(cluster)
        cls._hbase_validation(cluster)

        cls._flume_validation(cluster)
        cls._sentry_validation(cluster)
        cls._solr_validation(cluster)
        cls._sqoop_validation(cluster)
        cls._hbase_indexer_validation(cluster)
        cls._impala_validation(cluster)
        cls._kms_validation(cluster)

        cls._hdfs_ha_validation(cluster)
        cls._yarn_ha_validation(cluster)

    @classmethod
    def _basic_validation(cls, cluster):

        mng_count = cls.get_inst_count(cluster, 'CLOUDERA_MANAGER')
        if mng_count != 1:
            raise ex.InvalidComponentCountException('CLOUDERA_MANAGER',
                                                    1, mng_count)

        nn_count = cls.get_inst_count(cluster, 'HDFS_NAMENODE')
        if nn_count != 1:
            raise ex.InvalidComponentCountException(
                'HDFS_NAMENODE', 1, nn_count)

        snn_count = cls.get_inst_count(cluster, 'HDFS_SECONDARYNAMENODE')
        if snn_count != 1:
            raise ex.InvalidComponentCountException('HDFS_SECONDARYNAMENODE',
                                                    1, snn_count)
        dn_count = cls.get_inst_count(cluster, 'HDFS_DATANODE')
        replicas = cls.PU.get_config_value('HDFS', 'dfs_replication', cluster)
        if dn_count < replicas:
            raise ex.InvalidComponentCountException(
                'HDFS_DATANODE', replicas, dn_count,
                _('Number of datanodes must be not'
                  ' less than dfs_replication.'))

        rm_count = cls.get_inst_count(cluster, 'YARN_RESOURCEMANAGER')
        if rm_count > 1:
            raise ex.InvalidComponentCountException('YARN_RESOURCEMANAGER',
                                                    _('0 or 1'), rm_count)

        hs_count = cls.get_inst_count(cluster, 'YARN_JOBHISTORY')
        if hs_count > 1:
            raise ex.InvalidComponentCountException('YARN_JOBHISTORY',
                                                    _('0 or 1'),
                                                    hs_count)

        if rm_count > 0 and hs_count < 1:
            raise ex.RequiredServiceMissingException(
                'YARN_JOBHISTORY', required_by='YARN_RESOURCEMANAGER')

        nm_count = cls.get_inst_count(cluster, 'YARN_NODEMANAGER')
        if rm_count == 0:
            if nm_count > 0:
                raise ex.RequiredServiceMissingException(
                    'YARN_RESOURCEMANAGER', required_by='YARN_NODEMANAGER')

    @classmethod
    def _oozie_validation(cls, cluster):

        oo_count = cls.get_inst_count(cluster, 'OOZIE_SERVER')
        dn_count = cls.get_inst_count(cluster, 'HDFS_DATANODE')
        nm_count = cls.get_inst_count(cluster, 'YARN_NODEMANAGER')
        hs_count = cls.get_inst_count(cluster, 'YARN_JOBHISTORY')

        if oo_count > 1:
            raise ex.InvalidComponentCountException(
                'OOZIE_SERVER', _('0 or 1'),       oo_count)

        if oo_count == 1:
            if dn_count < 1:
                raise ex.RequiredServiceMissingException(
                    'HDFS_DATANODE', required_by='OOZIE_SERVER')

            if nm_count < 1:
                raise ex.RequiredServiceMissingException(
                    'YARN_NODEMANAGER', required_by='OOZIE_SERVER')

            if hs_count != 1:
                raise ex.RequiredServiceMissingException(
                    'YARN_JOBHISTORY', required_by='OOZIE_SERVER')

    @classmethod
    def _hive_validation(cls, cluster):
        hms_count = cls.get_inst_count(cluster, 'HIVE_METASTORE')
        hvs_count = cls.get_inst_count(cluster, 'HIVE_SERVER2')
        whc_count = cls.get_inst_count(cluster, 'HIVE_WEBHCAT')
        rm_count = cls.get_inst_count(cluster, 'YARN_RESOURCEMANAGER')

        if hms_count and rm_count < 1:
            raise ex.RequiredServiceMissingException(
                'YARN_RESOURCEMANAGER', required_by='HIVE_METASTORE')

        if hms_count and not hvs_count:
            raise ex.RequiredServiceMissingException(
                'HIVE_SERVER2', required_by='HIVE_METASTORE')

        if hvs_count and not hms_count:
            raise ex.RequiredServiceMissingException(
                'HIVE_METASTORE', required_by='HIVE_SERVER2')

        if whc_count and not hms_count:
            raise ex.RequiredServiceMissingException(
                'HIVE_METASTORE', required_by='WEBHCAT')

    @classmethod
    def _hue_validation(cls, cluster):
        hue_count = cls.get_inst_count(cluster, 'HUE_SERVER')
        if hue_count > 1:
            raise ex.InvalidComponentCountException(
                'HUE_SERVER', _('0 or 1'),      hue_count)

        shs_count = cls.get_inst_count(cluster, 'SPARK_YARN_HISTORY_SERVER')
        hms_count = cls.get_inst_count(cluster, 'HIVE_METASTORE')
        oo_count = cls.get_inst_count(cluster, 'OOZIE_SERVER')
        rm_count = cls.get_inst_count(cluster, 'YARN_RESOURCEMANAGER')

        if shs_count > 1:
            raise ex.InvalidComponentCountException(
                'SPARK_YARN_HISTORY_SERVER',
                _('0 or 1'), shs_count)
        if shs_count and not rm_count:
            raise ex.RequiredServiceMissingException(
                'YARN_RESOURCEMANAGER',
                required_by='SPARK_YARN_HISTORY_SERVER')

        if oo_count < 1 and hue_count:
            raise ex.RequiredServiceMissingException(
                'OOZIE_SERVER', required_by='HUE_SERVER')

        if hms_count < 1 and hue_count:
            raise ex.RequiredServiceMissingException(
                'HIVE_METASTORE', required_by='HUE_SERVER')

    @classmethod
    def _hbase_validation(cls, cluster):
        hbm_count = cls.get_inst_count(cluster, 'HBASE_MASTER')
        hbr_count = cls.get_inst_count(cluster, 'HBASE_REGIONSERVER')
        zk_count = cls.get_inst_count(cluster, 'ZOOKEEPER_SERVER')

        if hbm_count == 1:
            if zk_count < 1:
                raise ex.RequiredServiceMissingException(
                    'ZOOKEEPER', required_by='HBASE')
            if hbr_count < 1:
                raise ex.InvalidComponentCountException(
                    'HBASE_REGIONSERVER', _('at least 1'), hbr_count)
        elif hbm_count > 1:
            raise ex.InvalidComponentCountException('HBASE_MASTER',
                                                    _('0 or 1'), hbm_count)
        elif hbr_count >= 1:
            raise ex.InvalidComponentCountException('HBASE_MASTER',
                                                    _('at least 1'), hbm_count)

    @classmethod
    def validate_additional_ng_scaling(cls, cluster, additional):
        rm = cls.PU.get_resourcemanager(cluster)
        scalable_processes = cls._get_scalable_processes()

        for ng_id in additional:
            ng = gu.get_by_id(cluster.node_groups, ng_id)
            if not set(ng.node_processes).issubset(scalable_processes):
                msg = _("CDH plugin cannot scale nodegroup with processes: "
                        "%(processes)s")
                raise ex.NodeGroupCannotBeScaled(
                    ng.name, msg % {'processes': ' '.join(ng.node_processes)})

            if not rm and 'YARN_NODEMANAGER' in ng.node_processes:
                msg = _("CDH plugin cannot scale node group with processes "
                        "which have no master-processes run in cluster")
                raise ex.NodeGroupCannotBeScaled(ng.name, msg)

    @classmethod
    def validate_existing_ng_scaling(cls, cluster, existing):
        scalable_processes = cls._get_scalable_processes()
        dn_to_delete = 0
        for ng in cluster.node_groups:
            if ng.id in existing:
                if (ng.count > existing[ng.id] and
                        "HDFS_DATANODE" in ng.node_processes):
                    dn_to_delete += ng.count - existing[ng.id]

                if not set(ng.node_processes).issubset(scalable_processes):
                    msg = _("CDH plugin cannot scale nodegroup"
                            " with processes: %(processes)s")
                    raise ex.NodeGroupCannotBeScaled(
                        ng.name,
                        msg % {'processes': ' '.join(ng.node_processes)})

        dn_count = cls.get_inst_count(cluster, 'HDFS_DATANODE') - dn_to_delete
        replicas = cls.PU.get_config_value('HDFS', 'dfs_replication', cluster)
        if dn_count < replicas:
            raise ex.ClusterCannotBeScaled(
                cluster, _('Number of datanodes must be not'
                           ' less than dfs_replication.'))

    @classmethod
    def _get_scalable_processes(cls):
        return ['HDFS_DATANODE', 'YARN_NODEMANAGER']

    @classmethod
    def _flume_validation(cls, cluster):
        a_count = cls.get_inst_count(cluster, 'FLUME_AGENT')
        dn_count = cls.get_inst_count(cluster, 'HDFS_DATANODE')

        if a_count >= 1:
            if dn_count < 1:
                raise ex.RequiredServiceMissingException(
                    'HDFS_DATANODE', required_by='FLUME_AGENT')

    @classmethod
    def _sentry_validation(cls, cluster):

        snt_count = cls.get_inst_count(cluster, 'SENTRY_SERVER')
        dn_count = cls.get_inst_count(cluster, 'HDFS_DATANODE')
        zk_count = cls.get_inst_count(cluster, 'ZOOKEEPER_SERVER')

        if snt_count > 1:
            raise ex.InvalidComponentCountException(
                'SENTRY_SERVER', _('0 or 1'), snt_count)
        if snt_count == 1:
            if dn_count < 1:
                raise ex.RequiredServiceMissingException(
                    'HDFS_DATANODE', required_by='SENTRY_SERVER')
            if zk_count < 1:
                raise ex.RequiredServiceMissingException(
                    'ZOOKEEPER', required_by='SENTRY_SERVER')

    @classmethod
    def _solr_validation(cls, cluster):
        slr_count = cls.get_inst_count(cluster, 'SOLR_SERVER')
        zk_count = cls.get_inst_count(cluster, 'ZOOKEEPER_SERVER')
        dn_count = cls.get_inst_count(cluster, 'HDFS_DATANODE')

        if slr_count >= 1:
            if dn_count < 1:
                raise ex.RequiredServiceMissingException(
                    'HDFS_DATANODE', required_by='SOLR_SERVER')
            if zk_count < 1:
                raise ex.RequiredServiceMissingException(
                    'ZOOKEEPER', required_by='SOLR_SERVER')

    @classmethod
    def _sqoop_validation(cls, cluster):

        s2s_count = cls.get_inst_count(cluster, 'SQOOP_SERVER')
        dn_count = cls.get_inst_count(cluster, 'HDFS_DATANODE')
        hs_count = cls.get_inst_count(cluster, 'YARN_JOBHISTORY')
        nm_count = cls.get_inst_count(cluster, 'YARN_NODEMANAGER')

        if s2s_count > 1:
            raise ex.InvalidComponentCountException(
                'SQOOP_SERVER', _('0 or 1'), s2s_count)
        if s2s_count == 1:
            if dn_count < 1:
                raise ex.RequiredServiceMissingException(
                    'HDFS_DATANODE', required_by='SQOOP_SERVER')
            if nm_count < 1:
                raise ex.RequiredServiceMissingException(
                    'YARN_NODEMANAGER', required_by='SQOOP_SERVER')
            if hs_count != 1:
                raise ex.RequiredServiceMissingException(
                    'YARN_JOBHISTORY', required_by='SQOOP_SERVER')

    @classmethod
    def _hbase_indexer_validation(cls, cluster):

        lhbi_count = cls.get_inst_count(cluster, 'HBASE_INDEXER')
        zk_count = cls.get_inst_count(cluster, 'ZOOKEEPER_SERVER')
        dn_count = cls.get_inst_count(cluster, 'HDFS_DATANODE')
        slr_count = cls.get_inst_count(cluster, 'SOLR_SERVER')
        hbm_count = cls.get_inst_count(cluster, 'HBASE_MASTER')

        if lhbi_count >= 1:
            if dn_count < 1:
                raise ex.RequiredServiceMissingException(
                    'HDFS_DATANODE', required_by='HBASE_INDEXER')
            if zk_count < 1:
                raise ex.RequiredServiceMissingException(
                    'ZOOKEEPER', required_by='HBASE_INDEXER')
            if slr_count < 1:
                raise ex.RequiredServiceMissingException(
                    'SOLR_SERVER', required_by='HBASE_INDEXER')
            if hbm_count < 1:
                raise ex.RequiredServiceMissingException(
                    'HBASE_MASTER', required_by='HBASE_INDEXER')

    @classmethod
    def _impala_validation(cls, cluster):
        ics_count = cls.get_inst_count(cluster, 'IMPALA_CATALOGSERVER')
        iss_count = cls.get_inst_count(cluster, 'IMPALA_STATESTORE')
        id_count = cls.get_inst_count(cluster, 'IMPALAD')
        dn_count = cls.get_inst_count(cluster, 'HDFS_DATANODE')
        hms_count = cls.get_inst_count(cluster, 'HIVE_METASTORE')

        if ics_count > 1:
            raise ex.InvalidComponentCountException('IMPALA_CATALOGSERVER',
                                                    _('0 or 1'), ics_count)
        if iss_count > 1:
            raise ex.InvalidComponentCountException('IMPALA_STATESTORE',
                                                    _('0 or 1'), iss_count)
        if ics_count == 1:
            datanode_ng = u.get_node_groups(cluster, "HDFS_DATANODE")
            impalad_ng = u.get_node_groups(cluster, "IMPALAD")
            datanodes = set(ng.id for ng in datanode_ng)
            impalads = set(ng.id for ng in impalad_ng)

            if datanodes != impalads:
                raise ex.InvalidClusterTopology(
                    _("IMPALAD must be installed on every HDFS_DATANODE"))

            if iss_count != 1:
                raise ex.RequiredServiceMissingException(
                    'IMPALA_STATESTORE', required_by='IMPALA')
            if id_count < 1:
                raise ex.RequiredServiceMissingException(
                    'IMPALAD', required_by='IMPALA')
            if dn_count < 1:
                raise ex.RequiredServiceMissingException(
                    'HDFS_DATANODE', required_by='IMPALA')
            if hms_count < 1:
                raise ex.RequiredServiceMissingException(
                    'HIVE_METASTORE', required_by='IMPALA')

    @classmethod
    def _kms_validation(cls, cluster):

        kms_count = cls.get_inst_count(cluster, 'KMS')
        if kms_count > 1:
            raise ex.InvalidComponentCountException('KMS',
                                                    _('0 or 1'), kms_count)

    @classmethod
    def _hdfs_ha_validation(cls, cluster):
        jn_count = cls.get_inst_count(cluster, 'HDFS_JOURNALNODE')
        zk_count = cls.get_inst_count(cluster, 'ZOOKEEPER_SERVER')

        require_anti_affinity = cls.PU.c_helper.get_required_anti_affinity(
            cluster)

        if jn_count > 0:
            if jn_count < 3:
                raise ex.InvalidComponentCountException('HDFS_JOURNALNODE',
                                                        _('not less than 3'),
                                                        jn_count)
            if not jn_count % 2:
                raise ex.InvalidComponentCountException('HDFS_JOURNALNODE',
                                                        _('be odd'), jn_count)
            if zk_count < 1:
                raise ex.RequiredServiceMissingException('ZOOKEEPER',
                                                         required_by='HDFS HA')
            if require_anti_affinity:
                if 'HDFS_SECONDARYNAMENODE' not in \
                        cls._get_anti_affinity(cluster):
                    raise ex.NameNodeHAConfigurationError(
                        _('HDFS_SECONDARYNAMENODE should be enabled '
                          'in anti_affinity.'))
                if 'HDFS_NAMENODE' not in cls._get_anti_affinity(cluster):
                    raise ex.NameNodeHAConfigurationError(
                        _('HDFS_NAMENODE should be enabled in anti_affinity.'))

    @classmethod
    def _yarn_ha_validation(cls, cluster):
        rm_count = cls.get_inst_count(cluster, 'YARN_RESOURCEMANAGER')
        zk_count = cls.get_inst_count(cluster, 'ZOOKEEPER_SERVER')
        stdb_rm_count = cls.get_inst_count(cluster, 'YARN_STANDBYRM')

        require_anti_affinity = cls.PU.c_helper.get_required_anti_affinity(
            cluster)

        if stdb_rm_count > 1:
            raise ex.InvalidComponentCountException(
                'YARN_STANDBYRM', _('0 or 1'), stdb_rm_count)
        if stdb_rm_count > 0:
            if rm_count < 1:
                raise ex.RequiredServiceMissingException(
                    'YARN_RESOURCEMANAGER', required_by='RM HA')
            if zk_count < 1:
                raise ex.RequiredServiceMissingException(
                    'ZOOKEEPER', required_by='RM HA')
            if require_anti_affinity:
                if 'YARN_RESOURCEMANAGER' not in \
                        cls._get_anti_affinity(cluster):
                    raise ex.ResourceManagerHAConfigurationError(
                        _('YARN_RESOURCEMANAGER should be enabled in '
                          'anti_affinity.'))
                if 'YARN_STANDBYRM' not in cls._get_anti_affinity(cluster):
                    raise ex.ResourceManagerHAConfigurationError(
                        _('YARN_STANDBYRM should be'
                          ' enabled in anti_affinity.'))

    @classmethod
    def _get_anti_affinity(cls, cluster):
        return cluster.anti_affinity

    @classmethod
    def get_inst_count(cls, cluster, process):
        return sum([ng.count for ng in u.get_node_groups(cluster, process)])
