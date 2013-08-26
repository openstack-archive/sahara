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

import contextlib
import json
import os
import telnetlib
import time

import keystoneclient.v2_0
import requests
import unittest2

import savanna.tests.integration.configs.parameters.common_parameters as param
import savanna.tests.integration.configs.parameters.hdp_parameters as hdp_param
import savanna.tests.integration.configs.parameters.vanilla_parameters as v_prm
from savanna.utils import remote


def enable_test(test):
    def function(fun):
        if test:
            return fun
        else:
            return unittest2.skip('Test is disabled')(fun)

    return function


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
        print('URL = %s \n data = %s \n response = %s \n data = %s \n'
              % (URL, body, resp.status_code, data))
        return resp

    def _put(self, url, body):
        URL = self.baseurl + url
        resp = requests.put(URL, data=body, headers={
            'x-auth-token': self.token, 'Content-Type': 'application/json'})
        data = json.loads(resp.content)
        print('URL = %s \n data = %s \n response = %s \n data = %s \n'
              % (URL, body, resp.status_code, data))
        return resp

    def _get(self, url, printing):
        URL = self.baseurl + url
        resp = requests.get(URL, headers={'x-auth-token': self.token})
        if printing:
            print('URL = %s \n response = %s \n' % (URL, resp.status_code))
        if resp.status_code != 200:
            data = json.loads(resp.content)
            print('data= %s \n' % data)
        return resp

    def _delete(self, url):
        URL = self.baseurl + url
        resp = requests.delete(URL, headers={'x-auth-token': self.token})
        print('URL = %s \n response = %s \n' % (URL, resp.status_code))
        if resp.status_code != 204:
            data = json.loads(resp.content)
            print('data= %s \n' % data)
        return resp

    def post_object(self, url, body, code):
        post = self._post(url, json.dumps(body))
        self.assertEqual(post.status_code, code)
        data = json.loads(post.content)
        return data

    def put_object(self, url, object_id, body, code):
        data = self._put(url + object_id, json.dumps(body))
        self.assertEqual(data.status_code, code)
        data = json.loads(data.content)
        return data

    def get_object(self, url, obj_id, code, printing=False):
        rv = self._get(url + obj_id, printing)
        self.assertEqual(rv.status_code, code)
        data = json.loads(rv.content)
        return data

    def del_object(self, url, obj_id, code):
        rv = self._delete(url + obj_id)
        self.assertEqual(rv.status_code, code)
        if rv.status_code != 204:
            data = json.loads(rv.content)
            return data

        else:
            return rv.status_code

    def crud_object(self, body, url):
        try:
            data = self.post_object(url, body, 202)
        except Exception as e:
            self.fail('Failure while object creation: ' + str(e))

        if url == self.url_cluster:
            crud_object = 'cluster'
            get_url = self.url_cluster_with_slash

        elif url == self.url_ngt:
            crud_object = 'node_group_template'
            get_url = self.url_ngt_with_slash

        else:
            crud_object = 'cluster_template'
            get_url = self.url_cl_tmpl_with_slash

        data = data[crud_object]
        object_id = data.get('id')

        if crud_object == 'cluster':
            cluster_state = self.get_cluster_state(object_id)
            #if cluster has no 'Active' state then cluster will be deleted
            # and raised exception with cluster state
            self.check_cluster_state(cluster_state, object_id)

        try:
            self.get_object(get_url, object_id, 200)
        except Exception as e:
            self.del_object(get_url, object_id, 204)
            self.fail('Failure while object info obtaining: ' + str(e))

        try:
            self.del_object(get_url, object_id, 204)
            if crud_object == 'cluster':
                time.sleep(5)
        except Exception as e:
            self.fail('Failure while object deletion: ' + str(e))

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
            name=gr_name,
            description=desc,
            flavor_id=param.FLAVOR_ID,
            plugin_name=v_prm.PLUGIN_NAME,
            hadoop_version=v_prm.HADOOP_VERSION,
            node_processes=processes,
            node_configs={
                'HDFS': {},
                'MapReduce': {}
            }
        )

        return group_template

    def make_cluster_template(self, name, ngt_list):
        cluster_template = dict(
            name=name,
            plugin_name=v_prm.PLUGIN_NAME,
            hadoop_version=v_prm.HADOOP_VERSION,
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

    def make_cl_body_cluster_template(self, cl_tmpl_id):
        cluster_body = dict(
            name=param.CLUSTER_NAME,
            plugin_name=v_prm.PLUGIN_NAME,
            hadoop_version=v_prm.HADOOP_VERSION,
            cluster_template_id=cl_tmpl_id,
            default_image_id=v_prm.IMAGE_ID,
            user_keypair_id=param.USER_KEYPAIR_ID
        )

        return cluster_body

    def base_cl_body_node_processes(self, plugin_name, hadoop_version,
                                    user_keypair_id, image_id):
        return dict(
            name=param.CLUSTER_NAME,
            plugin_name=plugin_name,
            hadoop_version=hadoop_version,
            user_keypair_id=user_keypair_id,
            default_image_id=image_id,
            cluster_configs={},
            node_groups=[]
        )

    def add_node_group_to_cluster_body(self, cluster_body, ng_name, processes,
                                       node_count):
        cluster_body['node_groups'].append(dict(
            name=ng_name,
            flavor_id=param.FLAVOR_ID,
            node_processes=processes,
            count=node_count
        ))

    def make_hdp_cl_body_node_processes(self, node_processes):
        cluster_body = self.base_cl_body_node_processes(
            hdp_param.PLUGIN_NAME,
            hdp_param.HADOOP_VERSION,
            param.USER_KEYPAIR_ID,
            hdp_param.IMAGE_ID
        )

        for process, node_count in node_processes.items():
            if process == 'JT+NN':
                processes = ['JOBTRACKER', 'NAMENODE', 'SECONDARY_NAMENODE',
                             'GANGLIA_SERVER', 'GANGLIA_MONITOR',
                             'NAGIOS_SERVER', 'AMBARI_SERVER', 'AMBARI_AGENT']
            ng_name = 'jt-nn'

            if process == 'TT+DN':
                processes = ['TASKTRACKER', 'DATANODE', 'GANGLIA_MONITOR',
                             'HDFS_CLIENT', 'MAPREDUCE_CLIENT',
                             'AMBARI_AGENT']
                ng_name = 'tt-dn'

            self.add_node_group_to_cluster_body(cluster_body, ng_name,
                                                processes, node_count)

        return cluster_body

    def make_vanilla_cl_body_node_processes(self, node_processes):
        cluster_body = self.base_cl_body_node_processes(
            v_prm.PLUGIN_NAME,
            v_prm.HADOOP_VERSION,
            param.USER_KEYPAIR_ID,
            v_prm.IMAGE_ID
        )

        for process, node_count in node_processes.items():
            processes = ['jobtracker', 'namenode']
            ng_name = 'jt-nn'

            if process == 'TT+DN':
                processes = ['tasktracker', 'datanode']
                ng_name = 'tt-dn'

            elif process == 'JT':
                processes = ['jobtracker']
                ng_name = 'jt'

            elif process == 'NN':
                processes = ['namenode']
                ng_name = 'nn'

            elif process == 'TT':
                processes = ['tasktracker']
                ng_name = 'tt'

            elif process == 'DN':
                processes = ['datanode']
                ng_name = 'dn'

            elif process == 'JT+TT+DN':
                processes = ['jobtracker', 'tasktracker', 'datanode']
                ng_name = 'jt-tt-dn'

            elif process == 'NN+TT+DN':
                processes = ['namenode', 'tasktracker', 'datanode']
                ng_name = 'nn-tt-dn'

            self.add_node_group_to_cluster_body(cluster_body, ng_name,
                                                processes, node_count)

        return cluster_body

    def make_cl_body_node_group_templates(self, ngt_id_list):
        cluster_body = dict(
            name=param.CLUSTER_NAME,
            plugin_name=v_prm.PLUGIN_NAME,
            hadoop_version=v_prm.HADOOP_VERSION,
            user_keypair_id=param.USER_KEYPAIR_ID,
            default_image_id=v_prm.IMAGE_ID,
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
        cluster_body = self.make_vanilla_cl_body_node_processes(node_processes)

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

#------------------------------helper_methods----------------------------------

    def check_cluster_state(self, cluster_state, cluster_id):
        if cluster_state == 'Error':
            self.del_object(self.url_cluster_with_slash, cluster_id, 204)
            self.fail('Cluster state == \'Error\'')

        if cluster_state != 'Active':
            self.del_object(self.url_cluster_with_slash, cluster_id, 204)
            self.fail(
                'Cluster state != \'Active\', passed %d minutes'
                % param.TIMEOUT)

    def get_cluster_state(self, object_id):
        get_data = self.get_object(self.url_cluster_with_slash, object_id, 200)
        get_data = get_data['cluster']
        i = 1
        while get_data['status'] != 'Active':
            print('GET_STATUS: ', get_data['status'])
            if get_data['status'] == 'Error':
                print('\n Data for cluster: ' + str(get_data) + '\n')

                return 'Error'

            if i > param.TIMEOUT * 6:
                print('\n Data for cluster: ' + str(get_data) + '\n')

                return get_data['status']

            get_data = self.get_object(
                self.url_cluster_with_slash, object_id, 200)
            get_data = get_data['cluster']
            time.sleep(10)
            i += 1

        return get_data['status']

    def get_object_id(self, object_type, data):
        data = data[object_type]
        return data['id']

    def ssh_connection(self, host, node_username):
        return remote.setup_ssh_connection(host, node_username,
                                           open(param.PATH_TO_SSH).read())

    def execute_command(self, host, cmd, node_username):
        with contextlib.closing(self.ssh_connection(host,
                                                    node_username)) as ssh:
            return remote.execute_command(ssh, cmd)

    def write_file_to(self, host, remote_file, data, node_username):
        with contextlib.closing(self.ssh_connection(host,
                                                    node_username)) as ssh:
            return remote.write_file_to(ssh.open_sftp(), remote_file, data)

    def read_file_from(self, host, remote_file, node_username):
        with contextlib.closing(self.ssh_connection(host,
                                                    node_username)) as ssh:
            return remote.read_file_from(ssh.open_sftp(), remote_file)

    def transfer_script_to_node(self, host, node_username,
                                script='hadoop_test/hadoop_test_script.sh'):
        self.write_file_to(str(host),
                           'script.sh',
                           open('%s/integration/%s' % (os.getcwd(),
                                                       script)).read(),
                           node_username)
        self.execute_command(str(host), 'chmod 777 script.sh', node_username)

    def try_telnet(self, host, port):
        try:
            telnetlib.Telnet(host, port)

        except Exception as e:
            self.fail('Telnet has failed: ' + str(e) +
                      '     NODE_IP: %s, PORT: %s' % (host, port))

    def create_cluster_and_get_id(self, cluster_body):
        data = self.post_object(self.url_cluster, cluster_body, 202)
        cluster_id = data['cluster']['id']

        cluster_state = self.get_cluster_state(cluster_id)
        #if cluster has no 'Active' state then cluster will be deleted
        # and raised exception with cluster state
        self.check_cluster_state(cluster_state, cluster_id)

        return cluster_id

    def create_cluster_using_ngt_and_get_id(self, cl_tmpl_id, name):
        try:
            clstr_body = self.make_cl_body_cluster_template(cl_tmpl_id)
            clstr_body['name'] = name
            return self.create_cluster_and_get_id(clstr_body)

        except Exception as e:
            self.del_object(self.url_cl_tmpl_with_slash, cl_tmpl_id, 204)
            self.fail('failure: ' + str(e))

    def get_instances_ip_and_node_processes_list(self, cluster_id):
        get_data = self.get_object(
            self.url_cluster_with_slash, cluster_id, 200, True)
        node_groups = get_data['cluster']['node_groups']

        instances_ip = {}

        for node_group in node_groups:
            instances = node_group['instances']
            for instance in instances:
                management_ip = instance['management_ip']
                instances_ip[management_ip] = \
                    node_group['node_processes']

        return instances_ip

    def get_namenode_ip_and_tt_dn_count(self, instances_ip, plugin_name):
        #This timeout is needed for deploying Hadoop services
        time.sleep(120)

        tasktracker_count = 0
        datanode_count = 0
        node_count = 0

        namenode_ip = ''

        portmap = {
            'jobtracker': param.JT_PORT,
            'namenode': param.NN_PORT,
            'tasktracker': param.TT_PORT,
            'datanode': param.DN_PORT,
            'secondary_namenode': param.SEC_NN_PORT
        }
        self.tt = 'tasktracker'
        self.dn = 'datanode'
        self.nn = 'namenode'

        if plugin_name == 'hdp':
            portmap = {
                'JOBTRACKER': param.JT_PORT,
                'NAMENODE': param.NN_PORT,
                'TASKTRACKER': param.TT_PORT,
                'DATANODE': param.DN_PORT,
                'SECONDARY_NAMENODE': param.SEC_NN_PORT
            }
            self.tt = 'TASKTRACKER'
            self.dn = 'DATANODE'
            self.nn = 'NAMENODE'

        for host, processes in instances_ip.items():
            self.try_telnet(host, '22')
            node_count += 1

            for process in processes:
                if process in portmap:
                    self.try_telnet(host, portmap[process])

            if self.tt in processes:
                tasktracker_count += 1

            if self.dn in processes:
                datanode_count += 1

            if self.nn in processes:
                namenode_ip = host

        return {
            'namenode_ip': namenode_ip,
            'tasktracker_count': tasktracker_count,
            'datanode_count': datanode_count,
            'node_count': node_count
        }

    def await_active_workers_for_namenode(self, data, node_username,
                                          hadoop_user):
        attempts_count = 100

        while True:
            active_tasktrackers_count = self.execute_command(
                data['namenode_ip'], 'sudo su -c "hadoop job \
                            -list-active-trackers" %s' % hadoop_user,
                node_username)[1]

            active_datanodes_count = int(
                self.execute_command(data['namenode_ip'],
                                     'sudo su -c "hadoop dfsadmin -report" %s \
                                     | grep "Datanodes available:.*" | awk \
                                     \'{print $3}\'' % hadoop_user,
                                     node_username)[1]
            )

            if not active_tasktrackers_count:
                active_tasktrackers_count = 0

            else:
                active_tasktrackers_count = \
                    len(active_tasktrackers_count[:-1].split('\n'))

            if (active_tasktrackers_count == data['tasktracker_count']) and (
                    active_datanodes_count == data['datanode_count']):
                break

            if attempts_count == 0:
                self.fail('Tasktracker or datanode cannot be started '
                          'within 5 minutes.')

            time.sleep(3)

            attempts_count -= 1
