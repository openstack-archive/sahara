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
import savanna.tests.integration.parameters as param
import unittest


class ITestCase(unittest.TestCase):

    def setUp(self):
        self.port = param.SAVANNA_PORT
        self.host = param.SAVANNA_HOST

        self.maxDiff = None

        self.baseurl = 'http://' + self.host + ':' + self.port

        self.keystone = keystone_client(
            username=param.OS_USERNAME,
            password=param.OS_PASSWORD,
            tenant_name=param.OS_TENANT_NAME,
            auth_url=param.OS_AUTH_URL
        )

        self.tenant = self.keystone.tenant_id
        self.token = self.keystone.auth_token

        self.flavor_id = param.FLAVOR_ID
        self.image_id = param.IMAGE_ID

        self.url_nt = '/v0.2/%s/node-templates' % self.tenant
        self.url_nt_with_slash = '/v0.2/%s/node-templates/' % self.tenant
        self.url_cluster = '/v0.2/%s/clusters' % self.tenant
        self.url_cl_with_slash = '/v0.2/%s/clusters/' % self.tenant

#----------------------CRUD_comands--------------------------------------------

    def post(self, url, body):
        URL = self.baseurl + url
        resp = requests.post(URL, data=body, headers={
            'x-auth-token': self.token, 'Content-Type': 'application/json'})
        data = json.loads(resp.content) if resp.status_code == 202 \
            else resp.content
        print('URL = %s\ndata = %s\nresponse = %s\ndata = %s\n'
              % (URL, body, resp.status_code, data))
        return resp

    def put(self, url, body):
        URL = self.baseurl + url
        resp = requests.put(URL, data=body, headers={
            'x-auth-token': self.token, 'Content-Type': 'application/json'})
        data = json.loads(resp.content)
        print('URL = %s\ndata = %s\nresponse = %s\ndata = %s\n'
              % (URL, body, resp.status_code, data))
        return resp

    def get(self, url, printing):
        URL = self.baseurl + url
        resp = requests.get(URL, headers={'x-auth-token': self.token})
        if printing:
            print('URL = %s\nresponse = %s\n' % (URL, resp.status_code))
        if resp.status_code != 200:
            data = json.loads(resp.content)
            print('data= %s\n') % data
        return resp

    def delete(self, url):
        URL = self.baseurl + url
        resp = requests.delete(URL, headers={'x-auth-token': self.token})
        print('URL = %s\nresponse = %s\n' % (URL, resp.status_code))
        if resp.status_code != 204:
            data = json.loads(resp.content)
            print('data= %s\n') % data
        return resp

    def _post_object(self, url, body, code):
        post = self.post(url, json.dumps(body))
        self.assertEquals(post.status_code, code)
        data = json.loads(post.content)
        return data

    def _get_object(self, url, obj_id, code, printing=False):
        rv = self.get(url + obj_id, printing)
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

#----------------------other_commands------------------------------------------

    def _get_body_nt(self, name, nt_type, hs1, hs2):
        node = 'name' if nt_type in ['JT+NN', 'NN'] else 'data'
        tracker = 'job' if nt_type in ['JT+NN', 'JT'] else 'task'
        processes_name = nt_type
        nt = {
            u'name': u'%s.%s' % (name, param.FLAVOR_ID),
            u'%s_node' % node: {u'heap_size': u'%d' % hs1},
            u'%s_tracker' % tracker: {u'heap_size': u'%d' % hs2},
            u'node_type': {
                u'processes': [u'%s_tracker' % tracker,
                               u'%s_node' % node],
                u'name': u'%s' % processes_name},
            u'flavor_id': u'%s' % self.flavor_id
        }
        if nt_type == 'NN':
            del nt[u'%s_tracker' % tracker]
            nt[u'node_type'][u'processes'] = [u'%s_node' % node]
        elif nt_type == 'JT':
            del nt[u'%s_node' % node]
            nt[u'node_type'][u'processes'] = [u'%s_tracker' % tracker]
        return nt

    def _get_body_cluster(self, name, master_name, worker_name, node_number):
        return {
            u'status': u'Starting',
            u'service_urls': {},
            u'name': u'%s' % name,
            u'base_image_id': u'%s' % self.image_id,
            u'node_templates':
            {
                u'%s.%s' % (master_name, param.FLAVOR_ID): 1,
                u'%s.%s' % (worker_name, param.FLAVOR_ID): node_number
            },
            u'nodes': []
        }

    def change_field_nt(self, data, old_field, new_field):
        val = data['node_template'][old_field]
        del data['node_template'][old_field]
        data['node_template'][new_field] = val
        return data

    def make_nt(self, nt_name, node_type, jt_heap_size, nn_heap_size):
        nt = dict(
            node_template=dict(
                name='%s.%s' % (nt_name, param.FLAVOR_ID),
                node_type='JT+NN',
                flavor_id=self.flavor_id,
                job_tracker={
                    'heap_size': '%d' % jt_heap_size
                },
                name_node={
                    'heap_size': '%d' % nn_heap_size
                }
            ))
        if node_type == 'TT+DN':
            nt['node_template']['node_type'] = 'TT+DN'
            nt = self.change_field_nt(nt, 'job_tracker', 'task_tracker')
            nt = self.change_field_nt(nt, 'name_node', 'data_node')
        elif node_type == 'NN':
            nt['node_template']['node_type'] = 'NN'
            del nt['node_template']['job_tracker']
        elif node_type == 'JT':
            nt['node_template']['node_type'] = 'JT'
            del nt['node_template']['name_node']
        return nt

    def make_cluster_body(self, cluster_name, name_master_node,
                          name_worker_node, number_workers):
        body = dict(
            cluster=dict(
                name=cluster_name,
                base_image_id=self.image_id,
                node_templates={
                    '%s.%s' % (name_master_node, param.FLAVOR_ID): 1,
                    '%s.%s' %
                    (name_worker_node, param.FLAVOR_ID): number_workers
                }
            ))
        return body

    def delete_node_template(self, data):
        data = data['node_template']
        object_id = data.pop(u'id')
        self._del_object(self.url_nt_with_slash, object_id, 204)

    def _crud_object(self, body, get_body, url):
        data = self._post_object(url, body, 202)
        get_url = None
        object_id = None
        try:
            obj = 'node_template' if url == self.url_nt else 'cluster'
            get_url = self.url_nt_with_slash if url == self.url_nt \
                else self.url_cl_with_slash
            data = data['%s' % obj]
            object_id = data.pop(u'id')
            self.assertEquals(data, get_body)
            get_data = self._get_object(get_url, object_id, 200)
            get_data = get_data['%s' % obj]
            del get_data[u'id']
            if obj == 'cluster':
                self._await_cluster_active(
                    get_body, get_data, get_url, object_id)
        except Exception as e:
            self.fail('failure:' + str(e))
        finally:
            self._del_object(get_url, object_id, 204)
        return object_id

    def _await_cluster_active(self, get_body, get_data, get_url, object_id):
        get_body[u'status'] = u'Active'
        del get_body[u'service_urls']
        del get_body[u'nodes']
        i = 1
        while get_data[u'status'] != u'Active':
            if i > int(param.TIMEOUT) * 6:
                self.fail(
                    'cluster not Starting -> Active, passed %d minutes'
                    % param.TIMEOUT)
            get_data = self._get_object(get_url, object_id, 200)
            get_data = get_data['cluster']
            del get_data[u'id']
            del get_data[u'service_urls']
            del get_data[u'nodes']
            eventlet.sleep(10)
            i += 1
        self.assertEquals(get_data, get_body)
