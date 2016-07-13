# Copyright (c) 2016 Mirantis Inc.
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
from sahara.plugins.cdh.v5_7_0 import plugin_utils as pu
from sahara.plugins.cdh import validation
from sahara.plugins import exceptions as ex
from sahara.plugins import utils as u


class ValidatorV570(validation.Validator):
    PU = pu.PluginUtilsV570()

    @classmethod
    def validate_cluster_creating(cls, cluster):
        super(ValidatorV570, cls).validate_cluster_creating(cluster)
        cls._hdfs_ha_validation(cluster)
        cls._yarn_ha_validation(cluster)
        cls._flume_validation(cluster)
        cls._sentry_validation(cluster)
        cls._solr_validation(cluster)
        cls._sqoop_validation(cluster)
        cls._hbase_indexer_validation(cluster)
        cls._impala_validation(cluster)
        cls._kms_validation(cluster)

    @classmethod
    def _hdfs_ha_validation(cls, cluster):
        jn_count = cls._get_inst_count(cluster, 'HDFS_JOURNALNODE')
        zk_count = cls._get_inst_count(cluster, 'ZOOKEEPER_SERVER')

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
                if 'HDFS_SECONDARYNAMENODE' not in\
                        cls._get_anti_affinity(cluster):
                    raise ex.NameNodeHAConfigurationError(
                        _('HDFS_SECONDARYNAMENODE should be enabled '
                          'in anti_affinity.'))
                if 'HDFS_NAMENODE' not in cls._get_anti_affinity(cluster):
                    raise ex.NameNodeHAConfigurationError(
                        _('HDFS_NAMENODE should be enabled in anti_affinity.'))

    @classmethod
    def _yarn_ha_validation(cls, cluster):
        rm_count = cls._get_inst_count(cluster, 'YARN_RESOURCEMANAGER')
        zk_count = cls._get_inst_count(cluster, 'ZOOKEEPER_SERVER')
        stdb_rm_count = cls._get_inst_count(cluster, 'YARN_STANDBYRM')

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
                if 'YARN_RESOURCEMANAGER' not in\
                        cls._get_anti_affinity(cluster):
                    raise ex.ResourceManagerHAConfigurationError(
                        _('YARN_RESOURCEMANAGER should be enabled in '
                          'anti_affinity.'))
                if 'YARN_STANDBYRM' not in cls._get_anti_affinity(cluster):
                    raise ex.ResourceManagerHAConfigurationError(
                        _('YARN_STANDBYRM should be'
                            ' enabled in anti_affinity.'))

    @classmethod
    def _flume_validation(cls, cluster):
        a_count = cls._get_inst_count(cluster, 'FLUME_AGENT')
        dn_count = cls._get_inst_count(cluster, 'HDFS_DATANODE')

        if a_count >= 1:
            if dn_count < 1:
                raise ex.RequiredServiceMissingException(
                    'HDFS_DATANODE', required_by='FLUME_AGENT')

    @classmethod
    def _sentry_validation(cls, cluster):

        snt_count = cls._get_inst_count(cluster, 'SENTRY_SERVER')
        dn_count = cls._get_inst_count(cluster, 'HDFS_DATANODE')
        zk_count = cls._get_inst_count(cluster, 'ZOOKEEPER_SERVER')

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
        slr_count = cls._get_inst_count(cluster, 'SOLR_SERVER')
        zk_count = cls._get_inst_count(cluster, 'ZOOKEEPER_SERVER')
        dn_count = cls._get_inst_count(cluster, 'HDFS_DATANODE')

        if slr_count >= 1:
            if dn_count < 1:
                raise ex.RequiredServiceMissingException(
                    'HDFS_DATANODE', required_by='SOLR_SERVER')
            if zk_count < 1:
                raise ex.RequiredServiceMissingException(
                    'ZOOKEEPER', required_by='SOLR_SERVER')

    @classmethod
    def _sqoop_validation(cls, cluster):

        s2s_count = cls._get_inst_count(cluster, 'SQOOP_SERVER')
        dn_count = cls._get_inst_count(cluster, 'HDFS_DATANODE')
        hs_count = cls._get_inst_count(cluster, 'YARN_JOBHISTORY')
        nm_count = cls._get_inst_count(cluster, 'YARN_NODEMANAGER')

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

        lhbi_count = cls._get_inst_count(cluster, 'HBASE_INDEXER')
        zk_count = cls._get_inst_count(cluster, 'ZOOKEEPER_SERVER')
        dn_count = cls._get_inst_count(cluster, 'HDFS_DATANODE')
        slr_count = cls._get_inst_count(cluster, 'SOLR_SERVER')
        hbm_count = cls._get_inst_count(cluster, 'HBASE_MASTER')

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
        ics_count = cls._get_inst_count(cluster, 'IMPALA_CATALOGSERVER')
        iss_count = cls._get_inst_count(cluster, 'IMPALA_STATESTORE')
        id_count = cls._get_inst_count(cluster, 'IMPALAD')
        dn_count = cls._get_inst_count(cluster, 'HDFS_DATANODE')
        hms_count = cls._get_inst_count(cluster, 'HIVE_METASTORE')

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

        kms_count = cls._get_inst_count(cluster, 'KMS')
        if kms_count > 1:
            raise ex.InvalidComponentCountException('KMS',
                                                    _('0 or 1'), kms_count)

    @classmethod
    def _get_anti_affinity(cls, cluster):
        return cluster.anti_affinity
