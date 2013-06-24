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
import time
import unittest2

import savanna.tests.integration.parameters as param


class ITestCase(unittest2.TestCase):

    def setUp(self):
        self.port = param.SAVANNA_PORT
        self.host = param.SAVANNA_HOST

        self.baseurl = 'http://' + self.host + ':' + self.port

        self.keystone = keystoneclient.v2_0.Client(
            username=param.OS_USERNAME,
            password=param.OS_PASSWORD,
            tenant_name=param.OS_TENANT_NAME,
            auth_url=param.OS_AUTH_URL
        )

        self.tenant = self.keystone.tenant_id
        self.token = self.keystone.auth_token

        self.flavor_id = param.FLAVOR_ID
        self.image_id = param.IMAGE_ID

        self.maxDiff = None

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

#----------------------methods_for_CRUD_operations-----------------------------

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

    def crud_object(self, body, url):
        data = self.post_object(url, body, 202)
        get_url = None
        object_id = None
        crud_object = None
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
            if crud_object == 'cluster':
                self.await_cluster_active(get_url, object_id)
        except Exception as e:
            self.fail('failure: ' + str(e))
        finally:
            self.del_object(get_url, object_id, 204)
            if crud_object == 'cluster':
                time.sleep(30)
        return object_id

    def await_cluster_active(self, get_url, object_id):
        get_data = self.get_object(get_url, object_id, 200)
        get_data = get_data['cluster']
        i = 1
        while get_data['status'] != 'Active':
            print 'GET_STATUS: ', get_data['status']
            if i > int(param.TIMEOUT) * 6:
                print("json for cluster: \n" + get_data + "\n")
                self.fail(
                    'cluster not Starting -> Active, passed %d minutes'
                    % param.TIMEOUT)
            get_data = self.get_object(get_url, object_id, 200)
            get_data = get_data['cluster']
            time.sleep(10)
            i += 1

    def get_object_id(self, obj, body):
        print(body)
        data = body['%s' % obj]
        return data['id']

#----------------------make_different_template_body----------------------------

    def make_node_group_template(self, gr_name, desc, n_proc):
        processes = ['tasktracker', 'datanode']
        if n_proc == 'JT+NN':
            processes = ['jobtracker', 'namenode']
        elif n_proc == 'JT':
            processes = ['jobtracker']
        elif n_proc == 'NN':
            processes = ['namenode']
        elif n_proc == 'TT':
            processes = ['tasktracker']
        elif n_proc == 'DN':
            processes = ['datanode']
        elif n_proc == 'NN+TT+DN':
            processes = ['namenode', 'tasktracker', 'datanode']
        elif n_proc == 'JT+TT+DN':
            processes = ['jobtracker', 'tasktracker', 'datanode']
        group_template = dict(
            name='%s' % gr_name,
            description='%s' % desc,
            flavor_id='%s' % self.flavor_id,
            plugin_name='%s' % param.PLUGIN_NAME,
            hadoop_version='%s' % param.HADOOP_VERSION,
            node_processes=processes,
            node_configs={
                'HDFS': {},
                'MAPREDUCE': {}
            }
        )
        return group_template

    def make_cluster_template(self, name, ngt_list):
        cluster_template = dict(
            name='%s' % name,
            plugin_name='%s' % param.PLUGIN_NAME,
            hadoop_version='%s' % param.HADOOP_VERSION,
            cluster_configs={},
            node_groups=[]
        )
        for key, value in ngt_list.items():
            ngt = dict(
                name='',
                node_group_template_id='',
                count=1
            )
            ngt['node_group_template_id'] = key
            ngt['count'] = value
            data = self.get_object(self.url_ngt_with_slash, key, 200)
            name = data['node_group_template']['name']
            ngt['name'] = name
            cluster_template['node_groups'].append(ngt)
        return cluster_template

    def make_cl_body_cluster_template(self, plugin_name, hadoop_ver,
                                      cl_tmpl_id):
        cluster_body = dict(
            name='%s' % param.CLUSTER_NAME_CRUD,
            plugin_name='%s' % plugin_name,
            hadoop_version='%s' % hadoop_ver,
            cluster_template_id='%s' % cl_tmpl_id,
            default_image_id='%s' % self.image_id,
            user_keypair_id='%s' % param.SSH_KEY
        )
        return cluster_body

    def make_cl_body_node_processes(self, node_processes):
        cluster_body = dict(
            name='%s' % param.CLUSTER_NAME_CRUD,
            plugin_name='%s' % param.PLUGIN_NAME,
            hadoop_version='%s' % param.HADOOP_VERSION,
            user_keypair_id='%s' % param.SSH_KEY,
            default_image_id='%s' % param.IMAGE_ID,
            cluster_configs={},
            node_groups=[]
        )
        for key, value in node_processes.items():
            processes = ['jobtracker', 'namenode']
            ng_name = 'jt_nn'
            if key == 'TT+DN':
                processes = ['tasktracker', 'datanode']
                ng_name = 'tt_dn'
            elif key == 'JT':
                processes = ['jobtracker']
                ng_name = 'jt'
            elif key == 'NN':
                processes = ['namenode']
                ng_name = 'nn'
            elif key == 'TT':
                processes = ['tasktracker']
                ng_name = 'tt'
            elif key == 'DN':
                processes = ['datanode']
                ng_name = 'dn'
            elif key == 'JT+TT+DN':
                processes = ['jobtracker', 'tasktracker', 'datanode']
                ng_name = 'jt_tt_dn'
            elif key == 'NN+TT+DN':
                processes = ['namenode', 'tasktracker', 'datanode']
                ng_name = 'nn_tt_dn'
            cluster_body['node_groups'].append(dict(
                name=ng_name,
                flavor_id=param.FLAVOR_ID,
                node_processes=processes,
                count=value
            ))
        return cluster_body

    def make_cl_body_node_group_templates(self, ngt_id_list):
        cluster_body = dict(
            name='%s' % param.CLUSTER_NAME_CRUD,
            plugin_name='%s' % param.PLUGIN_NAME,
            hadoop_version='%s' % param.HADOOP_VERSION,
            user_keypair_id='%s' % param.SSH_KEY,
            default_image_id='%s' % param.IMAGE_ID,
            cluster_configs={},
            node_groups=[]
        )
        for key, value in ngt_id_list.items():
            data = self.get_object(self.url_ngt_with_slash, key, 200)
            name = data['node_group_template']['name']
            cluster_body['node_groups'].append(dict(
                name=name,
                node_group_template_id=key,
                count=value
            ))
        return cluster_body

    def make_cl_node_processes_ngt(self, node_processes, ngt_id_list):
        cluster_body = self.make_cl_body_node_processes(node_processes)
        for key, value in ngt_id_list.items():
            data = self.get_object(self.url_ngt_with_slash, key, 200)
            name = data['node_group_template']['name']
            cluster_body['node_groups'].append(dict(
                name=name,
                node_group_template_id=key,
                count=value
            ))
        return cluster_body

#-------------------make_node_group_template_and_get_id------------------------

    def create_node_group_templates(self):
        self.id_tt = self.get_object_id(
            'node_group_template', self.post_object(
                self.url_ngt, self.make_node_group_template(
                    'worker-tt', 'qa probe', 'TT'), 202))
        self.id_jt = self.get_object_id(
            'node_group_template', self.post_object(
                self.url_ngt, self.make_node_group_template(
                    'master-jt', 'qa probe', 'JT'), 202))

        self.id_nn = self.get_object_id(
            'node_group_template', self.post_object(
                self.url_ngt, self.make_node_group_template(
                    'master-nn', 'qa probe', 'NN'), 202))

        self.id_dn = self.get_object_id(
            'node_group_template', self.post_object(
                self.url_ngt, self.make_node_group_template(
                    'worker-dn', 'qa probe', 'DN'), 202))

        self.id_tt_dn = self.get_object_id(
            'node_group_template', self.post_object(
                self.url_ngt, self.make_node_group_template(
                    'worker-tt-dn', 'qa probe', 'TT+DN'), 202))

        self.id_jt_nn = self.get_object_id(
            'node_group_template', self.post_object(
                self.url_ngt, self.make_node_group_template(
                    'master-jt-nn', 'qa probe', 'JT+NN'), 202))

        self.id_nn_tt_dn = self.get_object_id(
            'node_group_template', self.post_object(
                self.url_ngt, self.make_node_group_template(
                    'nn-tt-dn', 'qa probe', 'NN+TT+DN'), 202))

        self.id_jt_tt_dn = self.get_object_id(
            'node_group_template', self.post_object(
                self.url_ngt, self.make_node_group_template(
                    'jt-tt-dn', 'qa probe', 'JT+TT+DN'), 202))

#---------------------delete_node_group_template-------------------------------

    def delete_node_group_templates(self):
        self.del_object(self.url_ngt_with_slash, self.id_jt_nn, 204)
        self.del_object(self.url_ngt_with_slash, self.id_jt, 204)
        self.del_object(self.url_ngt_with_slash, self.id_nn, 204)
        self.del_object(self.url_ngt_with_slash, self.id_tt, 204)
        self.del_object(self.url_ngt_with_slash, self.id_dn, 204)
        self.del_object(self.url_ngt_with_slash, self.id_tt_dn, 204)
        self.del_object(self.url_ngt_with_slash, self.id_nn_tt_dn, 204)
        self.del_object(self.url_ngt_with_slash, self.id_jt_tt_dn, 204)
