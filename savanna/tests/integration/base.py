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

import json
import keystoneclient.v2_0
import requests
import savanna.tests.integration.parameters as param
import unittest2


class ITestCase(unittest2.TestCase):

    def setUp(self):
        self.port = param.SAVANNA_PORT
        self.host = param.SAVANNA_HOST

        self.maxDiff = None

        self.baseurl = 'http://' + self.host + ':' + self.port

        self.keystone = keystoneclient.v2_0.Client(
            username=param.OS_USERNAME,
            password=param.OS_PASSWORD,
            tenant_name=param.OS_TENANT_NAME,
            auth_url=param.OS_AUTH_URL
        )

        self.tenant = self.keystone.tenant_id
        self.token = self.keystone.auth_token

        self.url_version = '/'

        self.flavor_id = param.FLAVOR_ID
        self.image_id = param.IMAGE_ID

        self.url_version = '/'
        self.url_ngt = '/v1.0/%s/node-group-templates' % self.tenant
        self.url_ngt_with_slash = '/v1.0/%s/node-group-templates/'\
                                  % self.tenant
        self.url_cluster = '/v1.0/%s/clusters' % self.tenant
        self.url_cluster_with_slash = '/v1.0/%s/clusters/' % self.tenant
        self.url_cl_tmpl = '/v1.0/%s/cluster-templates' % self.tenant
        self.url_cl_tmpl_with_slash = '/v1.0/%s/cluster-templates/'\
                                      % self.tenant
        self.url_plugins = '/v1.0/%s/plugins' % self.tenant
        self.url_plugins_with_slash = '/v1.0/%s/plugins/' % self.tenant
        self.url_images = '/v1.0/%s/images' % self.tenant
        self.url_images_with_slash = '/v1.0/%s/images/' % self.tenant

#----------------------CRUD_comands--------------------------------------------

    def _post(self, url, body):
        URL = self.baseurl + url
        resp = requests.post(URL, data=body, headers={
            'x-auth-token': self.token, 'Content-Type': 'application/json'})
        data = json.loads(resp.content) if resp.status_code == 202 \
            else resp.content
        print('URL = %s\ndata = %s\nresponse = %s\ndata = %s\n'
              % (URL, body, resp.status_code, data))
        return resp

    def _put(self, url, body):
        URL = self.baseurl + url
        resp = requests.put(URL, data=body, headers={
            'x-auth-token': self.token, 'Content-Type': 'application/json'})
        data = json.loads(resp.content)
        print('URL = %s\ndata = %s\nresponse = %s\ndata = %s\n'
              % (URL, body, resp.status_code, data))
        return resp

    def _get(self, url, printing):
        URL = self.baseurl + url
        resp = requests.get(URL, headers={'x-auth-token': self.token})
        if printing:
            print('URL = %s\nresponse = %s\n' % (URL, resp.status_code))
        if resp.status_code != 200:
            data = json.loads(resp.content)
            print('data= %s\n') % data
        return resp

    def _delete(self, url):
        URL = self.baseurl + url
        resp = requests.delete(URL, headers={'x-auth-token': self.token})
        print('URL = %s\nresponse = %s\n' % (URL, resp.status_code))
        if resp.status_code != 204:
            data = json.loads(resp.content)
            print('data= %s\n') % data
        return resp

    def post_object(self, url, body, code):
        post = self._post(url, json.dumps(body))
        self.assertEquals(post.status_code, code)
        data = json.loads(post.content)
        return data

    def get_object(self, url, obj_id, code, printing=False):
        rv = self._get(url + obj_id, printing)
        self.assertEquals(rv.status_code, code)
        data = json.loads(rv.content)
        return data

    def del_object(self, url, obj_id, code):
        rv = self._delete(url + obj_id)
        self.assertEquals(rv.status_code, code)
        if rv.status_code != 204:
            data = json.loads(rv.content)
            return data
        else:
            return rv.status_code

#----------------------other_commands------------------------------------------

    def make_node_group_template(self, gr_name, desc, n_proc):
        processes = ["tasktracker", "datanode"]
        if n_proc == 'JT+NN':
            processes = ["jobtracker", "namenode"]
        elif n_proc == 'JT':
            processes = ["jobtracker"]
        elif n_proc == 'NN':
            processes = ["namenode"]
        elif n_proc == 'TT':
            processes = ["tasktracker"]
        elif n_proc == 'DN':
            processes = ["datanode"]
        group_template = dict(
            name="%s" % gr_name,
            description="%s" % desc,
            flavor_id="%s" % self.flavor_id,
            plugin_name="%s" % param.PLUGIN_NAME,
            hadoop_version="%s" % param.HADOOP_VERSION,
            node_processes=processes,
            node_configs={}
        )
        return group_template

    def make_cluster_template(self, name, ngt_list):
        cluster_template = dict(
            name="%s" % name,
            plugin_name="%s" % param.PLUGIN_NAME,
            hadoop_version="%s" % param.HADOOP_VERSION,
            cluster_configs={},
            node_groups=[]
        )
        for key, value in ngt_list.items():
            ngt = dict(
                name="",
                node_group_template_id="",
                count=1
            )
            ngt['node_group_template_id'] = key
            ngt['count'] = value
            data = self.get_object(self.url_ngt_with_slash, key, 200)
            name = data['node_group_template']['name']
            ngt['name'] = name
            cluster_template['node_groups'].append(ngt)
        return cluster_template

    def make_cl_body_with_cl_tmpl(self, plugin_name, hadoop_ver,
                                  cl_tmpl_id):
        cluster_body = dict(
            name="%s" % param.CLUSTER_NAME_CRUD,
            plugin_name="%s" % plugin_name,
            hadoop_version="%s" % hadoop_ver,
            cluster_template_id="%s" % cl_tmpl_id,
            default_image_id="%s" % self.image_id,
            user_keypair_id="%s" % param.SSH_KEY
        )
        return cluster_body

    def make_cl_body_with_ngt(self, ngt_list):
        cluster_body = dict(
            name="%s" % param.CLUSTER_NAME_CRUD,
            plugin_name="%s" % param.PLUGIN_NAME,
            hadoop_version="%s" % param.HADOOP_VERSION,
            user_keypair_id="%s" % param.SSH_KEY,
            default_image_id="%s" % param.IMAGE_ID,
            cluster_configs={},
            node_groups=[]
        )
        for key, value in ngt_list.items():
            ngt = dict(
                name="",
                node_group_template_id="",
                count=1
            )
            ngt['node_group_template_id'] = key
            ngt['count'] = value
            data = self.get_object(self.url_ngt_with_slash, key, 200)
            name = data['node_group_template']['name']
            ngt['name'] = name
            cluster_body['node_groups'].append(ngt)
        return cluster_body

    def get_object_id(self, obj, body):
        print(body)
        data = body['%s' % obj]
        return data['id']

    def crud_object(self, body, url):
        data = self.post_object(url, body, 202)
        get_url = None
        object_id = None
        try:
            if url == self.url_cluster:
                crud_object = 'cluster'
                get_url = self.url_cluster_with_slash
            elif url == self.url_ngt:
                crud_object = 'node_group_template'
                get_url = self.url_ngt_with_slash
            else:
                crud_object = 'cluster_template'
                get_url = self.url_cl_tmpl_with_slash
            data = data['%s' % crud_object]
            object_id = data.get('id')
            get_data = self.get_object(get_url, object_id, 200)
            get_data = get_data['%s' % crud_object]
            self.assertEquals(data, get_data)
        except Exception as e:
            self.fail('failure:' + e.message)
        finally:
            self.del_object(get_url, object_id, 204)
        return object_id
