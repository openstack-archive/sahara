# Copyright (c) 2013 Mirantis Inc.
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

import eventlet
import json
from keystoneclient.v2_0 import Client as keystone_client
import requests
import savanna.openstack.common.importutils as importutils
import unittest

_CONF = importutils.try_import("savanna.tests.integration.config")


def _get_conf(key, default):
    return getattr(_CONF, key) if _CONF and hasattr(_CONF, key) else default

OS_USERNAME = _get_conf("OS_USERNAME", "admin")
OS_PASSWORD = _get_conf("OS_PASSWORD", "nova")
OS_TENANT_NAME = _get_conf("OS_TENANT_NAME", "admin")
OS_AUTH_URL = _get_conf("OS_AUTH_URL", "http://localhost:35357/v2.0/")
SAVANNA_HOST = _get_conf("SAVANNA_HOST", "192.168.1.1")
SAVANNA_PORT = _get_conf("SAVANNA_PORT", "8080")
SAVANNA_IMAGE_ID = _get_conf("SAVANNA_IMAGE_ID", "42")

keystone = keystone_client(
    username=OS_USERNAME,
    password=OS_PASSWORD,
    tenant_name=OS_TENANT_NAME,
    auth_url=OS_AUTH_URL
)


class ValidationTestCase(unittest.TestCase):
    def setUp(self):
        self.host = SAVANNA_HOST
        self.maxDiff = None
        self.port = SAVANNA_PORT
        self.baseurl = 'http://' + self.host + ':' + self.port
        self.tenant = keystone.tenant_id
        self.token = keystone.auth_token
        self.flavor_id = 'm1.medium'
        self.image_id = SAVANNA_IMAGE_ID
        self.url_nt = '/v0.2/%s/node-templates' % self.tenant
        self.url_nt_not_json = '/v0.2/%s/node-templates/' % self.tenant

#----------------------add_value_for_node_templates----------------------------

        self.jtnn = dict(
            node_template=dict(
                name='test-template-1',
                node_type='JT+NN',
                flavor_id=self.flavor_id,
                job_tracker={
                    'heap_size': '1234'
                },
                name_node={
                    'heap_size': '2345'
                }
            ))
        self.ttdn = dict(
            node_template=dict(
                name='test-template-2',
                node_type='TT+DN',
                flavor_id=self.flavor_id,
                task_tracker={
                    'heap_size': '1234'
                },
                data_node={
                    'heap_size': '2345'
                }
            ))
        self.jt = dict(
            node_template=dict(
                name='test-template-3',
                node_type='JT',
                flavor_id=self.flavor_id,
                job_tracker={
                    'heap_size': '1234'
                }
            ))
        self.nn = dict(
            node_template=dict(
                name='test-template-4',
                node_type='NN',
                flavor_id=self.flavor_id,
                name_node={
                    'heap_size': '2345'
                }
            ))
        self.tt = dict(
            node_template=dict(
                name='test-template-5',
                node_type='TT',
                flavor_id=self.flavor_id,
                task_tracker={
                    'heap_size': '2345'
                }
            ))
        self.dn = dict(
            node_template=dict(
                name='test-template-6',
                node_type='DN',
                flavor_id=self.flavor_id,
                data_node={
                    'heap_size': '2345'
                }
            ))

        self.get_ttdn = {
            u'name': u'test-template-2',
            u'data_node': {u'heap_size': u'2345'},
            u'task_tracker': {u'heap_size': u'1234'},
            u'node_type': {
                u'processes': [u'task_tracker',
                               u'data_node'],
                u'name': u'TT+DN'},
            u'flavor_id': u'm1.medium'
        }

        self.get_jtnn = {
            u'name': u'test-template-1',
            u'name_node': {u'heap_size': u'2345'},
            u'job_tracker': {u'heap_size': u'1234'},
            u'node_type': {
                u'processes': [u'job_tracker',
                               u'name_node'],
                u'name': u'JT+NN'},
            u'flavor_id': u'm1.medium'
        }

        self.get_nn = {
            u'name': u'test-template-4',
            u'name_node': {u'heap_size': u'2345'},
            u'node_type': {
                u'processes': [u'name_node'],
                u'name': u'NN'},
            u'flavor_id': u'm1.medium'
        }

        self.get_jt = {
            u'name': u'test-template-3',
            u'job_tracker': {u'heap_size': u'1234'},
            u'node_type': {
                u'processes': [u'job_tracker'],
                u'name': u'JT'},
            u'flavor_id': u'm1.medium'
        }

#----------------------add_value_for_clusters----------------------------------

        self.url_cluster = '/v0.2/%s/clusters' % self.tenant
        self.url_cluster_without_json = '/v0.2/%s/clusters/' % self.tenant

        self.cluster_data_jtnn_ttdn = dict(
            cluster=dict(
                name='QA-test-cluster',
                base_image_id=self.image_id,
                node_templates={
                    'jt_nn.medium': 1,
                    'tt_dn.medium': 2
                }
            ))

        self.cluster_data_jtnn_ttdn_small = dict(
            cluster=dict(
                name='QA-test-cluster',
                base_image_id=self.image_id,
                node_templates={
                    'jt_nn.small': 1,
                    'tt_dn.small': 1
                }
            ))

        self.cluster_data_jtnn = dict(
            cluster=dict(
                name='test-cluster',
                base_image_id=self.image_id,
                node_templates={
                    'jt_nn.medium': 1
                }
            ))

        self.get_cluster_data_jtnn_ttdn = {
            u'status': u'Starting',
            u'service_urls': {},
            u'name': u'QA-test-cluster',
            u'base_image_id': u'%s' % self.image_id,
            u'node_templates':
            {
                u'jt_nn.medium': 1,
                u'tt_dn.medium': 2
            },
            u'nodes': []
        }

        self.get_cluster_data_jtnn_ttdn_small = {
            u'status': u'Starting',
            u'service_urls': {},
            u'name': u'QA-test-cluster',
            u'base_image_id': u'%s' % self.image_id,
            u'node_templates':
            {
                u'jt_nn.small': 1,
                u'tt_dn.small': 1
            },
            u'nodes': []
        }

        self.get_cluster_data_jtnn = {
            u'status': u'Starting',
            u'service_urls': {},
            u'name': u'test-cluster',
            u'base_image_id': u'%s' % self.image_id,
            u'node_templates':
            {
                u'jt_nn.medium': 1
            },
            u'nodes': []
        }

#---------------------close_setUp----------------------------------------------

    def post(self, url, body):
        URL = self.baseurl + url
        resp = requests.post(URL, data=body, headers={
            "x-auth-token": self.token, "Content-Type": "application/json"})
        if resp.status_code == 202:
            data = json.loads(resp.content)
        else:
            data = resp.content
        print("URL = %s\ndata = %s\nresponse = %s\ndata = %s\n"
              % (URL, body, resp.status_code, data))
        return resp

    def put(self, url, body):
        URL = self.baseurl + url
        resp = requests.put(URL, data=body, headers={
            "x-auth-token": self.token, "Content-Type": "application/json"})
        data = json.loads(resp.content)
        print("URL = %s\ndata = %s\nresponse = %s\ndata = %s\n"
              % (URL, body, resp.status_code, data))
        return resp

    def get(self, url):
        URL = self.baseurl + url
        resp = requests.get(URL, headers={"x-auth-token": self.token})
        print("URL = %s\nresponse = %s\n" % (URL, resp.status_code))
        if resp.status_code != 200:
            data = json.loads(resp.content)
            print("data= %s\n") % data
        return resp

    def delete(self, url):
        URL = self.baseurl + url
        resp = requests.delete(URL, headers={"x-auth-token": self.token})
        print("URL = %s\nresponse = %s\n" % (URL, resp.status_code))
        if resp.status_code != 204:
            data = json.loads(resp.content)
            print("data= %s\n") % data
        return resp

    def _post_object(self, url, body, code):
        post = self.post(url, json.dumps(body))
        self.assertEquals(post.status_code, code)
        data = json.loads(post.content)
        return data

    def _get_object(self, url, obj_id, code):
        rv = self.get(url + obj_id)
        self.assertEquals(rv.status_code, code)
        data = json.loads(rv.content)
        return data

    def _del_object(self, url, obj_id, code):
        rv = self.delete(url + obj_id)
        self.assertEquals(rv.status_code, code)
        if rv.status_code != 204:
            data = json.loads(rv.content)
            return data
        else:
            code = self.delete(url + obj_id).status_code
            while code != 404:
                eventlet.sleep(1)
                code = self.delete(url + obj_id).status_code

    def _crud_object(self, body, get_body, url):
        data = self._post_object(url, body, 202)
        get_url = None
        object_id = None
        try:
            obj = "cluster"
            get_url = self.url_cluster_without_json
            if url == self.url_nt:
                obj = "node_template"
                get_url = self.url_nt_not_json
            data = data["%s" % obj]
            object_id = data.pop(u'id')
            self.assertEquals(data, get_body)
            get_data = self._get_object(get_url, object_id, 200)
            get_data = get_data['%s' % obj]
            del get_data[u'id']
            if obj == "cluster":
                self._asrtCluster(get_body, get_data, get_url, object_id)
        except Exception as e:
            print("failure:" + str(e))
        finally:
            self._del_object(get_url, object_id, 204)
        return object_id

    def _asrtCluster(self, get_body, get_data, get_url, object_id):
        get_body[u'status'] = u'Active'
        del get_body[u'service_urls']
        del get_body[u'nodes']
        i = 1
        while get_data[u'status'] != u'Active':
            if i > 60:
                print(self.fail(
                    "cluster not Starting -> Active, remaining 10 minutes"))
            get_data = self._get_object(get_url, object_id, 200)
            get_data = get_data['cluster']
            del get_data[u'id']
            del get_data[u'service_urls']
            del get_data[u'nodes']
            eventlet.sleep(10)
            i += 1
        self.assertEquals(get_data, get_body)
