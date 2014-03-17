# Copyright (c) 2013 Intel Corporation
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

import mock
from requests import sessions

from sahara import exceptions as ex
from sahara.plugins.intel import exceptions as iex
from sahara.plugins.intel.v2_5_1 import client as c
from sahara.tests.unit import base
from sahara.tests.unit.plugins.intel.v2_5_1 import response as r


SESSION_POST_DATA = {'sessionID': '123'}
SESSION_GET_DATA = {"items": [
    {
        "nodeprogress": {
            "hostname": 'host',
            'info': '_ALLFINISH\n'
        }
    }
]}


class TestClient(base.SaharaTestCase):
    def _get_instance(self):
        inst_remote = mock.MagicMock()
        inst_remote.get_http_client.return_value = sessions.Session()
        inst_remote.__enter__.return_value = inst_remote

        inst = mock.MagicMock()
        inst.remote.return_value = inst_remote

        return inst

    @mock.patch('requests.sessions.Session.post')
    @mock.patch('requests.sessions.Session.get')
    def test_cluster_op(self, get, post):
        client = c.IntelClient(self._get_instance(), 'rty')

        data = {'lelik': 'bolik'}

        post.return_value = r.make_resp(data)
        self.assertEqual(client.cluster.create(), data)

        get.return_value = r.make_resp(data)
        self.assertEqual(client.cluster.get(), data)

        post.return_value = r.make_resp(SESSION_POST_DATA)
        get.return_value = r.make_resp(SESSION_GET_DATA)
        client.cluster.install_software(['bla-bla'])

        self.assertEqual(post.call_count, 2)
        self.assertEqual(get.call_count, 2)

    @mock.patch('requests.sessions.Session.delete')
    @mock.patch('requests.sessions.Session.post')
    @mock.patch('requests.sessions.Session.get')
    def test_nodes_op(self, get, post, delete):
        client = c.IntelClient(self._get_instance(), 'rty')

        # add
        post.return_value = r.make_resp(data={
            "items": [
                {
                    "iporhostname": "n1",
                    "info": "Connected"
                },
                {
                    "iporhostname": "n2",
                    "info": "Connected"
                }
            ]
        })
        client.nodes.add(['n1', 'n2'], 'hadoop', '/Def', '/tmp/key')
        post.return_value = r.make_resp(data={
            "items": [
                {
                    "iporhostname": "n1",
                    "info": "bla-bla"
                }
            ]
        })
        self.assertRaises(iex.IntelPluginException, client.nodes.add,
                          ['n1'], 'hadoop', '/Def', '/tmp/key')

        # config
        post.return_value = r.make_resp(SESSION_POST_DATA)
        get.return_value = r.make_resp(SESSION_GET_DATA)
        client.nodes.config()

        # delete
        delete.return_value = r.make_resp()
        client.nodes.delete(['n1'])

        # get
        get.return_value = r.make_resp()
        client.nodes.get()

        # get_status
        get.return_value = r.make_resp(data={"status": "running"})
        client.nodes.get_status(['n1'])

        # stop_nodes
        post.return_value = r.make_resp()
        client.nodes.stop(['n1'])

        self.assertEqual(delete.call_count, 1)
        self.assertEqual(post.call_count, 4)
        self.assertEqual(get.call_count, 3)

    @mock.patch('requests.sessions.Session.put')
    @mock.patch('requests.sessions.Session.post')
    def test_params_op(self, post, put):
        client = c.IntelClient(self._get_instance(), 'rty')
        post.return_value = r.make_resp()
        put.return_value = r.make_resp()

        # add
        client.params.hdfs.add('lelik', 'bolik')
        client.params.hadoop.add('lelik', 'bolik')
        client.params.mapred.add('lelik', 'bolik')

        # get
        self.assertRaises(ex.NotImplementedException, client.params.hdfs.get,
                          ['n1'], 'lelik')
        self.assertRaises(ex.NotImplementedException, client.params.hadoop.get,
                          ['n1'], 'lelik')
        self.assertRaises(ex.NotImplementedException, client.params.mapred.get,
                          ['n1'], 'lelik')

        # update
        client.params.hdfs.update('lelik', 'bolik', nodes=['n1'])
        client.params.hdfs.update('lelik', 'bolik')
        client.params.hadoop.update('lelik', 'bolik', nodes=['n1'])
        client.params.hadoop.update('lelik', 'bolik')
        client.params.mapred.update('lelik', 'bolik', nodes=['n1'])
        client.params.mapred.update('lelik', 'bolik')

        self.assertEqual(post.call_count, 3)
        self.assertEqual(put.call_count, 6)

    @mock.patch('sahara.context.sleep', lambda x: None)
    @mock.patch('requests.sessions.Session.post')
    @mock.patch('requests.sessions.Session.get')
    def test_base_services_op(self, get, post):
        client = c.IntelClient(self._get_instance(), 'rty')

        # start
        post.return_value = r.make_resp()
        get.return_value = r.make_resp(data={
            "items": [
                {
                    "serviceName": "hdfs",
                    "status": "running"
                },
                {
                    "serviceName": "mapred",
                    "status": "running"
                }
            ]})
        client.services.hdfs.start()
        client.services.mapred.start()

        get.return_value = r.make_resp(data={
            "items": [
                {
                    "serviceName": "hdfs",
                    "status": "stopped"
                },
                {
                    "serviceName": "mapred",
                    "status": "stopped"
                }
            ]
        })

        self.assertRaises(iex.IntelPluginException,
                          client.services.hdfs.start)
        self.assertRaises(iex.IntelPluginException,
                          client.services.mapred.start)

        # stop
        post.return_value = r.make_resp()
        client.services.hdfs.stop()
        client.services.mapred.stop()

        # service
        get.return_value = r.make_resp(data={
            "items": [
                {
                    "serviceName": "bla-bla",
                    "status": "fail"
                }
            ]
        })

        self.assertRaises(iex.IntelPluginException,
                          client.services.hdfs.status)
        self.assertRaises(iex.IntelPluginException,
                          client.services.mapred.status)

        # get_nodes
        get.return_value = r.make_resp()
        client.services.hdfs.get_nodes()
        client.services.mapred.get_nodes()

        # add_nodes
        post.return_value = r.make_resp()
        client.services.hdfs.add_nodes('DataNode', ['n1', 'n2'])
        client.services.mapred.add_nodes('NameNode', ['n1', 'n2'])

        self.assertEqual(get.call_count, 606)
        self.assertEqual(post.call_count, 8)

    @mock.patch('requests.sessions.Session.delete')
    @mock.patch('requests.sessions.Session.post')
    @mock.patch('requests.sessions.Session.get')
    def test_services_op(self, get, post, delete):
        client = c.IntelClient(self._get_instance(), 'rty')

        # add
        post.return_value = r.make_resp()
        client.services.add(['hdfs', 'mapred'])

        # get_services
        get.return_value = r.make_resp()
        client.services.get_services()

        # delete_service
        delete.return_value = r.make_resp()
        client.services.delete_service('hdfs')

    @mock.patch('requests.sessions.Session.post')
    @mock.patch('requests.sessions.Session.get')
    def test_hdfs_services_op(self, get, post):
        client = c.IntelClient(self._get_instance(), 'rty')

        # format
        get.return_value = r.make_resp(SESSION_GET_DATA)
        post.return_value = r.make_resp(SESSION_POST_DATA)
        client.services.hdfs.format()

        # decommission
        post.return_value = r.make_resp()
        client.services.hdfs.decommission_nodes(['n1'])

        # get status
        get.return_value = r.make_resp(data={
            "items": [
                {
                    "hostname": "n1",
                    "status": "start"
                }
            ]
        })
        client.services.hdfs.get_datanodes_status()
        self.assertEqual(client.services.hdfs.get_datanode_status('n1'),
                         'start')
        self.assertRaises(iex.IntelPluginException,
                          client.services.hdfs.get_datanode_status, 'n2')

        self.assertEqual(get.call_count, 4)
        self.assertEqual(post.call_count, 2)

    @mock.patch('sahara.context.sleep', lambda x: None)
    @mock.patch('requests.sessions.Session.post')
    @mock.patch('requests.sessions.Session.get')
    def test_session_op(self, get, post):
        client = c.IntelClient(self._get_instance(), 'rty')

        data1 = {
            "items": [
                {
                    "nodeprogress": {
                        "hostname": 'host',
                        'info': 'info\n'
                    }
                }
            ]
        }
        data2 = {
            "items": [
                {
                    "nodeprogress": {
                        "hostname": 'host',
                        'info': '_ALLFINISH\n'
                    }
                }
            ]
        }

        get.side_effect = (r.make_resp(data1), r.make_resp(data2))
        post.return_value = r.make_resp(SESSION_POST_DATA)

        client.services.hdfs.format()

        self.assertEqual(get.call_count, 2)
        self.assertEqual(post.call_count, 1)

    @mock.patch('requests.sessions.Session.get')
    def test_rest_client(self, get):
        client = c.IntelClient(self._get_instance(), 'rty')
        get.return_value = r.make_resp(ok=False, status_code=500, data={
            "message": "message"
        })
        self.assertRaises(iex.IntelPluginException,
                          client.services.get_services)
