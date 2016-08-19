# Copyright (c) 2015 Intel Corporation
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

from sahara.conductor import resource as res
from sahara.plugins.cdh import commands as cmd
from sahara.plugins.cdh import plugin_utils as pu
from sahara.plugins.cdh.v5_5_0 import config_helper
from sahara.plugins.cdh.v5_5_0 import db_helper
from sahara.plugins import utils as u


class PluginUtilsV550(pu.AbstractPluginUtils):

    def __init__(self):
        self.c_helper = config_helper.ConfigHelperV550()
        self.db_helper = db_helper

    def get_role_name(self, instance, service):
        # NOTE: role name must match regexp "[_A-Za-z][-_A-Za-z0-9]{0,63}"
        shortcuts = {
            'AGENT': 'A',
            'ALERTPUBLISHER': 'AP',
            'CATALOGSERVER': 'ICS',
            'DATANODE': 'DN',
            'EVENTSERVER': 'ES',
            'HBASE_INDEXER': 'LHBI',
            'HIVEMETASTORE': 'HVM',
            'HIVESERVER2': 'HVS',
            'HOSTMONITOR': 'HM',
            'IMPALAD': 'ID',
            'JOBHISTORY': 'JS',
            'JOURNALNODE': 'JN',
            'KAFKA_BROKER': 'KB',
            'KMS': 'KMS',
            'MASTER': 'M',
            'NAMENODE': 'NN',
            'NODEMANAGER': 'NM',
            'OOZIE_SERVER': 'OS',
            'REGIONSERVER': 'RS',
            'RESOURCEMANAGER': 'RM',
            'SECONDARYNAMENODE': 'SNN',
            'SENTRY_SERVER': 'SNT',
            'SERVER': 'S',
            'SERVICEMONITOR': 'SM',
            'SOLR_SERVER': 'SLR',
            'SPARK_YARN_HISTORY_SERVER': 'SHS',
            'SQOOP_SERVER': 'S2S',
            'STATESTORE': 'ISS',
            'WEBHCAT': 'WHC',
            'HDFS_GATEWAY': 'HG',
            'YARN_GATEWAY': 'YG'
        }
        return '%s_%s' % (shortcuts.get(service, service),
                          instance.hostname().replace('-', '_'))

    def get_sentry(self, cluster):
        return u.get_instance(cluster, 'SENTRY_SERVER')

    def get_flumes(self, cluster):
        return u.get_instances(cluster, 'FLUME_AGENT')

    def get_solrs(self, cluster):
        return u.get_instances(cluster, 'SOLR_SERVER')

    def get_sqoop(self, cluster):
        return u.get_instance(cluster, 'SQOOP_SERVER')

    def get_hbase_indexers(self, cluster):
        return u.get_instances(cluster, 'KEY_VALUE_STORE_INDEXER')

    def get_catalogserver(self, cluster):
        return u.get_instance(cluster, 'IMPALA_CATALOGSERVER')

    def get_statestore(self, cluster):
        return u.get_instance(cluster, 'IMPALA_STATESTORE')

    def get_impalads(self, cluster):
        return u.get_instances(cluster, 'IMPALAD')

    def get_kms(self, cluster):
        return u.get_instances(cluster, 'KMS')

    def get_jns(self, cluster):
        return u.get_instances(cluster, 'HDFS_JOURNALNODE')

    def get_stdb_rm(self, cluster):
        return u.get_instance(cluster, 'YARN_STANDBYRM')

    def get_kafka_brokers(self, cluster):
        return u.get_instances(cluster, 'KAFKA_BROKER')

    def convert_process_configs(self, configs):
        p_dict = {
            "CLOUDERA": ['MANAGER'],
            "NAMENODE": ['NAMENODE'],
            "DATANODE": ['DATANODE'],
            "SECONDARYNAMENODE": ['SECONDARYNAMENODE'],
            "RESOURCEMANAGER": ['RESOURCEMANAGER'],
            "NODEMANAGER": ['NODEMANAGER'],
            "JOBHISTORY": ['JOBHISTORY'],
            "OOZIE": ['OOZIE_SERVER'],
            "HIVESERVER": ['HIVESERVER2'],
            "HIVEMETASTORE": ['HIVEMETASTORE'],
            "WEBHCAT": ['WEBHCAT'],
            "HUE": ['HUE_SERVER'],
            "SPARK_ON_YARN": ['SPARK_YARN_HISTORY_SERVER'],
            "ZOOKEEPER": ['SERVER'],
            "MASTER": ['MASTER'],
            "REGIONSERVER": ['REGIONSERVER'],
            "FLUME": ['AGENT'],
            "CATALOGSERVER": ['CATALOGSERVER'],
            "STATESTORE": ['STATESTORE'],
            "IMPALAD": ['IMPALAD'],
            "KS_INDEXER": ['HBASE_INDEXER'],
            "SENTRY": ['SENTRY_SERVER'],
            "SOLR": ['SOLR_SERVER'],
            "SQOOP": ['SQOOP_SERVER'],
            "KMS": ['KMS'],
            "YARN_GATEWAY": ['YARN_GATEWAY'],
            "HDFS_GATEWAY": ['HDFS_GATEWAY'],
            "JOURNALNODE": ['JOURNALNODE'],
            "KAFKA": ['KAFKA_BROKER']
        }
        if isinstance(configs, res.Resource):
            configs = configs.to_dict()
        for k in configs.keys():
            if k in p_dict.keys():
                item = configs[k]
                del configs[k]
                newkey = p_dict[k][0]
                configs[newkey] = item
        return res.Resource(configs)

    def configure_sentry(self, cluster):
        manager = self.get_manager(cluster)
        with manager.remote() as r:
            self.db_helper.create_sentry_database(cluster, r)

    def _configure_repo_from_inst(self, instance):
        super(PluginUtilsV550, self)._configure_repo_from_inst(instance)

        cluster = instance.cluster
        with instance.remote() as r:
            if cmd.is_ubuntu_os(r):
                kms_key = (
                    self.c_helper.get_kms_key_url(cluster) or
                    self.c_helper.DEFAULT_KEY_TRUSTEE_UBUNTU_REPO_KEY_URL)
                kms_repo_url = self.c_helper.KEY_TRUSTEE_UBUNTU_REPO_URL
                cmd.add_ubuntu_repository(r, kms_repo_url, 'kms')
                cmd.add_apt_key(r, kms_key)
                cmd.update_repository(r)
            if cmd.is_centos_os(r):
                kms_repo_url = self.c_helper.KEY_TRUSTEE_CENTOS_REPO_URL
                cmd.add_centos_repository(r, kms_repo_url, 'kms')
                cmd.update_repository(r)
