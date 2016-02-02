# Copyright (c) 2015 Intel Corpration
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

from sahara.plugins.cdh.v5_4_0 import validation
from sahara.plugins import exceptions as ex
from sahara.tests.unit.plugins.cdh import base_validation_tests as bvt

icte = ex.InvalidClusterTopology
nnce = ex.NameNodeHAConfigurationError
icce = ex.InvalidComponentCountException
rsme = ex.RequiredServiceMissingException
rmce = ex.ResourceManagerHAConfigurationError


class ValidationTestCase(bvt.BaseValidationTestCase):

    def setUp(self):
        super(ValidationTestCase, self).setUp()
        self.module = validation.ValidatorV540

    def _get_test_cases(self):
        cases = super(ValidationTestCase, self)._get_test_cases()

        disable_anti_affinity = {'cluster_configs': {'general': {
            'Require Anti Affinity': False}}}
        cases += [
            [None, {'HDFS_JOURNALNODE': 3,
                    'ZOOKEEPER_SERVER': 1}, [], disable_anti_affinity],
            [rsme, {'HDFS_JOURNALNODE': 3,
                    'ZOOKEEPER_SERVER': 0}, [], disable_anti_affinity],
            [icce, {'HDFS_JOURNALNODE': 4,
                    'ZOOKEEPER_SERVER': 1}, [], disable_anti_affinity],
            [icce, {'HDFS_JOURNALNODE': 2,
                    'ZOOKEEPER_SERVER': 1}, [], disable_anti_affinity],
            [nnce, {'HDFS_JOURNALNODE': 3, 'ZOOKEEPER_SERVER': 1}, [],
             {'anti_affinity': ['HDFS_SECONDARYNAMENODE']}],
            [nnce, {'HDFS_JOURNALNODE': 3, 'ZOOKEEPER_SERVER': 1}, [],
             {'anti_affinity': ['HDFS_NAMENODE']}],
            [None, {'HDFS_JOURNALNODE': 3, 'ZOOKEEPER_SERVER': 1}, [],
             {'anti_affinity': ['HDFS_NAMENODE', 'HDFS_SECONDARYNAMENODE']}],
            [None, {'YARN_STANDBYRM': 1,
                    'ZOOKEEPER_SERVER': 1}, [], disable_anti_affinity],
            [icce, {'YARN_STANDBYRM': 2,
                    'ZOOKEEPER_SERVER': 1}, [], disable_anti_affinity],
            [rsme, {'YARN_STANDBYRM': 1,
                    'ZOOKEEPER_SERVER': 0}, [], disable_anti_affinity],
            [rmce, {'YARN_STANDBYRM': 1, 'ZOOKEEPER_SERVER': 1}, [],
             {'anti_affinity': ['YARN_RESOURCEMANAGER']}],
            [rmce, {'YARN_STANDBYRM': 1, 'ZOOKEEPER_SERVER': 1}, [],
             {'anti_affinity': ['YARN_STANDBYRM']}],
            [None, {'YARN_STANDBYRM': 1, 'ZOOKEEPER_SERVER': 1}, [],
             {'anti_affinity': ['YARN_STANDBYRM', 'YARN_RESOURCEMANAGER']}],
        ]

        cases += [
            [None, {'FLUME_AGENT': 1}],
            [icce, {'ZOOKEEPER_SERVER': 1, 'SENTRY_SERVER': 2}],
            [None, {'ZOOKEEPER_SERVER': 1, 'SENTRY_SERVER': 1}],
            [rsme, {'ZOOKEEPER_SERVER': 0, 'SENTRY_SERVER': 1}],
            [None, {'ZOOKEEPER_SERVER': 1, 'SOLR_SERVER': 1}],
            [rsme, {'ZOOKEEPER_SERVER': 0, 'SOLR_SERVER': 1}],
            [None, {'YARN_NODEMANAGER': 1, 'YARN_JOBHISTORY': 1,
                    'SQOOP_SERVER': 1}],
            [rsme, {'YARN_NODEMANAGER': 0, 'YARN_JOBHISTORY': 1,
                    'SQOOP_SERVER': 1}],
            [rsme, {'YARN_NODEMANAGER': 1, 'YARN_JOBHISTORY': 0,
                    'SQOOP_SERVER': 1}],
            # HBASE_MASTER AND HBASE_REGIONSERVER depend circularly
            [None, {'ZOOKEEPER_SERVER': 1, 'SOLR_SERVER': 1,
                    'HBASE_MASTER': 1, 'HBASE_INDEXER': 1,
                    'HBASE_REGIONSERVER': 1}],
            [rsme, {'ZOOKEEPER_SERVER': 0, 'SOLR_SERVER': 1,
                    'HBASE_MASTER': 1, 'HBASE_INDEXER': 1,
                    'HBASE_REGIONSERVER': 1}],
            [rsme, {'ZOOKEEPER_SERVER': 1, 'SOLR_SERVER': 0,
                    'HBASE_MASTER': 1, 'HBASE_INDEXER': 1,
                    'HBASE_REGIONSERVER': 1}],
            [rsme, {'ZOOKEEPER_SERVER': 1, 'SOLR_SERVER': 1,
                    'HBASE_MASTER': 0, 'HBASE_INDEXER': 1}],
        ]

        worker_with_implama = ('worker_ng', 1, ['HDFS_DATANODE',
                                                'YARN_NODEMANAGER',
                                                'IMPALAD'], 3)
        cases += [
            [None, {'IMPALA_CATALOGSERVER': 1, 'IMPALA_STATESTORE': 1,
                    'HIVE_METASTORE': 1, 'HIVE_SERVER2': 1,
                    'HDFS_DATANODE': 0, 'YARN_NODEMANAGER': 0},
             [worker_with_implama]],
            [icte, {'IMPALA_CATALOGSERVER': 1, 'IMPALA_STATESTORE': 1,
                    'HIVE_METASTORE': 1, 'HIVE_SERVER2': 1},
             []],
            [icte, {'IMPALA_CATALOGSERVER': 1, 'IMPALA_STATESTORE': 1,
                    'HIVE_METASTORE': 1, 'HIVE_SERVER2': 1},
             [worker_with_implama]],
            [rsme, {'IMPALA_CATALOGSERVER': 1, 'IMPALA_STATESTORE': 0,
                    'HIVE_METASTORE': 1, 'HIVE_SERVER2': 1,
                    'HDFS_DATANODE': 0, 'YARN_NODEMANAGER': 0},
             [worker_with_implama]],
            [rsme, {'IMPALA_CATALOGSERVER': 1, 'IMPALA_STATESTORE': 1,
                    'HIVE_METASTORE': 0, 'HIVE_SERVER2': 1,
                    'HDFS_DATANODE': 0, 'YARN_NODEMANAGER': 0},
             [worker_with_implama]]

        ]

        cases += [
            [None, {'KMS': 1}],
            [icce, {'KMS': 2}]
        ]
        return cases
