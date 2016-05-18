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

import copy

import mock

from sahara.plugins.ambari import ha_helper as ha
from sahara.tests.unit import base


class HAHelperTestCase(base.SaharaTestCase):

    def setUp(self):
        super(HAHelperTestCase, self).setUp()
        self.cluster = mock.MagicMock()
        self.cluster.name = "clusterName"
        for i in range(1, 4):
            instance = mock.MagicMock()
            instance.fqdn.return_value = "in{}".format(i)
            instance.instance_name = "in{}name".format(i)
            setattr(self, "in{}".format(i), instance)
        self.bp = {
            "host_groups": [
                {
                    "components": [
                        {"name": "NAMENODE"}
                    ]
                }
            ],
            "configurations": [
                {"hdfs-site": {}},
                {"yarn-site": {}},
                {"core-site": {}},
                {"hadoop-env": {}},
                {"zoo.cfg": {}}
            ]
        }

    @mock.patch("sahara.plugins.ambari.ha_helper._set_high_zk_limits")
    @mock.patch("sahara.plugins.ambari.ha_helper._set_default_fs")
    def test_update_bp_ha_common(self, mock__set_default_fs,
                                 mock__set_high_zk_limits):
        ha.update_bp_ha_common(self.cluster, copy.deepcopy(self.bp))
        self.assertTrue(mock__set_default_fs.called)
        self.assertTrue(mock__set_high_zk_limits.called)

    @mock.patch("sahara.plugins.ambari.ha_helper._configure_hdfs_site")
    @mock.patch("sahara.plugins.ambari.ha_helper._set_zk_quorum")
    @mock.patch("sahara.plugins.ambari.ha_helper._add_zkfc_to_namenodes")
    def test_update_bp_for_namenode_ha(self, mock__add_zkfc_to_namenodes,
                                       mock__set_zk_quorum,
                                       mock__configure_hdfs_site):
        ha.update_bp_for_namenode_ha(self.cluster, copy.deepcopy(self.bp))
        self.assertTrue(mock__add_zkfc_to_namenodes.called)
        self.assertTrue(mock__set_zk_quorum.called)
        self.assertTrue(mock__configure_hdfs_site.called)

    @mock.patch("sahara.plugins.ambari.ha_helper._set_default_fs")
    @mock.patch("sahara.plugins.ambari.ha_helper._set_zk_quorum")
    @mock.patch("sahara.plugins.ambari.ha_helper._configure_yarn_site")
    def test_update_bp_for_resourcemanager_ha(self, mock__configure_yarn_site,
                                              mock__set_zk_quorum,
                                              mock__set_default_fs):
        ha.update_bp_for_resourcemanager_ha(self.cluster,
                                            copy.deepcopy(self.bp))
        self.assertTrue(mock__configure_yarn_site.called)
        self.assertTrue(mock__set_zk_quorum.called)
        self.assertTrue(mock__set_default_fs.called)

    @mock.patch("sahara.plugins.ambari.ha_helper._confgure_hbase_site")
    def test_update_bp_for_hbase_ha(self, mock__confgure_hbase_site):
        ha.update_bp_for_hbase_ha(self.cluster, copy.deepcopy(self.bp))
        self.assertTrue(mock__confgure_hbase_site.called)

    def test__add_zkfc_to_namenodes(self):
        bp = ha._add_zkfc_to_namenodes(copy.deepcopy(self.bp))
        self.assertIn({"name": "ZKFC"}, bp["host_groups"][0]["components"])

    @mock.patch("sahara.plugins.utils.get_instances")
    def test__set_default_fs(self, mock_get_instances):
        bp = ha._set_default_fs(self.cluster, copy.deepcopy(self.bp),
                                ha.p_common.NAMENODE_HA)
        self.assertEqual("hdfs://hdfs-ha",
                         ha._find_core_site(bp)["fs.defaultFS"])

        mock_get_instances.return_value = [self.in1]
        bp = ha._set_default_fs(self.cluster, copy.deepcopy(self.bp),
                                ha.p_common.RESOURCEMANAGER_HA)
        self.assertEqual("hdfs://{}:8020".format(self.in1.fqdn()),
                         ha._find_core_site(bp)["fs.defaultFS"])

    @mock.patch("sahara.plugins.utils.get_instances")
    def test__set_zk_quorum(self, mock_get_instances):
        mock_get_instances.return_value = [self.in1, self.in2, self.in3]
        bp = ha._set_zk_quorum(self.cluster, copy.deepcopy(self.bp),
                               ha.CORE_SITE)
        self.assertEqual(
            "{}:2181,{}:2181,{}:2181".format(
                self.in1.fqdn(), self.in2.fqdn(), self.in3.fqdn()),
            ha._find_core_site(bp)['ha.zookeeper.quorum'])

        bp = ha._set_zk_quorum(self.cluster, copy.deepcopy(self.bp),
                               ha.YARN_SITE)
        self.assertEqual(
            "{}:2181,{}:2181,{}:2181".format(
                self.in1.fqdn(), self.in2.fqdn(), self.in3.fqdn()),
            ha._find_yarn_site(bp)['hadoop.registry.zk.quorum'])

    def test__set_high_zk_limits(self):
        bp = ha._set_high_zk_limits(copy.deepcopy(self.bp))
        self.assertEqual("10000", ha._find_zoo_cfg(bp)["tickTime"])

    @mock.patch("sahara.plugins.utils.get_instances")
    def test__set_primary_and_standby_namenode(self, mock_get_instances):
        mock_get_instances.return_value = [self.in1, self.in2]
        bp = ha._set_primary_and_standby_namenode(self.cluster,
                                                  copy.deepcopy(self.bp))
        self.assertEqual(
            self.in1.fqdn(),
            ha._find_hadoop_env(bp)['dfs_ha_initial_namenode_active'])
        self.assertEqual(
            self.in2.fqdn(),
            ha._find_hadoop_env(bp)['dfs_ha_initial_namenode_standby'])

    @mock.patch("sahara.plugins.utils.get_instances")
    def test__configure_hdfs_site(self, mock_get_instances):
        mock_get_instances.return_value = [self.in1, self.in2]
        bp = ha._configure_hdfs_site(self.cluster, copy.deepcopy(self.bp))

        j_nodes = ";".join(
            ["{}:8485".format(i.fqdn()) for i in mock_get_instances()])
        nn_id_concat = ",".join(
            [i.instance_name for i in mock_get_instances()])
        result = {
            "hdfs-site": {
                "dfs.client.failover.proxy.provider.hdfs-ha":
                    "org.apache.hadoop.hdfs.server.namenode.ha."
                    "ConfiguredFailoverProxyProvider",
                "dfs.ha.automatic-failover.enabled": "true",
                "dfs.ha.fencing.methods": "shell(/bin/true)",
                "dfs.nameservices": "hdfs-ha",
                "dfs.namenode.shared.edits.dir":
                    "qjournal://{}/hdfs-ha".format(j_nodes),
                "dfs.ha.namenodes.hdfs-ha": nn_id_concat,
                "dfs.namenode.http-address": "{}:50070".format(
                    self.in1.fqdn()),
                "dfs.namenode.https-address": "{}:50470".format(
                    self.in1.fqdn()),
            }
        }
        prop = result["hdfs-site"]
        for i in mock_get_instances():
            prop["dfs.namenode.http-address.hdfs-ha.%s" % i.instance_name] = (
                "%s:50070" % i.fqdn())
            prop["dfs.namenode.https-address.hdfs-ha.%s" % i.instance_name] = (
                "%s:50470" % i.fqdn())
            prop["dfs.namenode.rpc-address.hdfs-ha.%s" % i.instance_name] = (
                "%s:8020" % i.fqdn())
        self.assertDictEqual(result["hdfs-site"], ha._find_hdfs_site(bp))

    @mock.patch("sahara.plugins.utils.get_instance")
    @mock.patch("sahara.plugins.utils.get_instances")
    def test__configure_yarn_site(self, mock_get_instances, mock_get_instance):
        mock_get_instances.return_value = [self.in1, self.in2, self.in3]
        mock_get_instance.return_value = self.in1
        bp = ha._configure_yarn_site(self.cluster, copy.deepcopy(self.bp))

        zks = ",".join(["%s:2181" % i.fqdn() for i in mock_get_instances()])
        rm_ids = ",".join([i.instance_name for i in mock_get_instances()])
        result = {
            "yarn-site": {
                "hadoop.registry.rm.enabled": "false",
                "yarn.resourcemanager.zk-address": zks,
                "yarn.log.server.url": "{}:19888/jobhistory/logs/".format(
                    mock_get_instance().fqdn()),
                "yarn.resourcemanager.address": "{}:8050".format(
                    mock_get_instances()[0].fqdn()),
                "yarn.resourcemanager.admin.address": "{}:8141".format(
                    mock_get_instances()[0].fqdn()),
                "yarn.resourcemanager.cluster-id": self.cluster.name,
                "yarn.resourcemanager.ha.automatic-failover.zk-base-path":
                    "/yarn-leader-election",
                "yarn.resourcemanager.ha.enabled": "true",
                "yarn.resourcemanager.ha.rm-ids": rm_ids,
                "yarn.resourcemanager.hostname":
                    mock_get_instances()[0].fqdn(),
                "yarn.resourcemanager.recovery.enabled": "true",
                "yarn.resourcemanager.resource-tracker.address":
                    "{}:8025".format(mock_get_instances()[0].fqdn()),
                "yarn.resourcemanager.scheduler.address": "{}:8030".format(
                    mock_get_instances()[0].fqdn()),
                "yarn.resourcemanager.store.class":
                    "org.apache.hadoop.yarn.server.resourcemanager.recovery."
                    "ZKRMStateStore",
                "yarn.resourcemanager.webapp.address": "{}:8088".format(
                    mock_get_instances()[0].fqdn()),
                "yarn.resourcemanager.webapp.https.address": "{}:8090".format(
                    mock_get_instances()[0].fqdn()),
                "yarn.timeline-service.address": "{}:10200".format(
                    mock_get_instance().fqdn()),
                "yarn.timeline-service.webapp.address": "{}:8188".format(
                    mock_get_instance().fqdn()),
                "yarn.timeline-service.webapp.https.address": "{}:8190".format(
                    mock_get_instance().fqdn())
            }
        }
        props = result["yarn-site"]
        for i in mock_get_instances():
            props["yarn.resourcemanager.hostname.{}".format(
                i.instance_name)] = i.fqdn()
            props["yarn.resourcemanager.webapp.address.{}".format(
                i.instance_name)] = "{}:8088".format(i.fqdn())
            props["yarn.resourcemanager.webapp.https.address.{}".format(
                i.instance_name)] = "{}:8090".format(i.fqdn())
        self.assertDictEqual(result["yarn-site"], ha._find_yarn_site(bp))

    @mock.patch("sahara.plugins.utils.get_instances")
    def test__confgure_hbase_site(self, mock_get_instances):
        mock_get_instances.return_value = [self.in1, self.in2, self.in3]
        bp = ha._confgure_hbase_site(self.cluster, copy.deepcopy(self.bp))

        result = {
            "hbase-site": {
                "hbase.regionserver.global.memstore.lowerLimit": "0.38",
                "hbase.regionserver.global.memstore.upperLimit": "0.4",
                "hbase.regionserver.handler.count": "60",
                "hbase.regionserver.info.port": "60030",
                "hbase.regionserver.storefile.refresh.period": "20",
                "hbase.rootdir": "hdfs://hdfs-ha/apps/hbase/data",
                "hbase.security.authentication": "simple",
                "hbase.security.authorization": "false",
                "hbase.superuser": "hbase",
                "hbase.tmp.dir": "/hadoop/hbase",
                "hbase.zookeeper.property.clientPort": "2181",
                "hbase.zookeeper.useMulti": "true",
                "hfile.block.cache.size": "0.40",
                "zookeeper.session.timeout": "30000",
                "zookeeper.znode.parent": "/hbase-unsecure",
                "hbase.zookeeper.quorum":
                    ",".join([i.fqdn() for i in mock_get_instances()])
            }
        }
        self.assertDictEqual(result["hbase-site"], ha._find_hbase_site(bp))
