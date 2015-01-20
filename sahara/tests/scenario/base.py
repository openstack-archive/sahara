# Copyright (c) 2015 Mirantis Inc.
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

from __future__ import print_function
import functools
import glob
import json
import os
import time

import fixtures
from oslo_utils import excutils
from tempest_lib import base
from tempest_lib import exceptions as exc

from sahara.tests.scenario import clients
from sahara.tests.scenario import utils

DEFAULT_TEMPLATES_PATH = (
    'sahara/tests/scenario/templates/%(plugin_name)s/%(hadoop_version)s')


def errormsg(message):
    def decorator(fct):
        @functools.wraps(fct)
        def wrapper(*args, **kwargs):
            try:
                return fct(*args, **kwargs)
            except Exception:
                with excutils.save_and_reraise_exception():
                    print(message)
        return wrapper
    return decorator


class BaseTestCase(base.BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(BaseTestCase, cls).setUpClass()
        cls.network = None
        cls.credentials = None
        cls.testcase = None

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self._init_clients()
        self.plugin_opts = {
            'plugin_name': self.testcase['plugin_name'],
            'hadoop_version': self.testcase['plugin_version']
        }
        self.template_path = DEFAULT_TEMPLATES_PATH % self.plugin_opts

    def _init_clients(self):
        username = self.credentials['os_username']
        password = self.credentials['os_password']
        tenant_name = self.credentials['os_tenant']
        auth_url = self.credentials['os_auth_url']
        sahara_url = self.credentials['sahara_url']

        self.sahara = clients.SaharaClient(username=username,
                                           api_key=password,
                                           project_name=tenant_name,
                                           auth_url=auth_url,
                                           sahara_url=sahara_url)
        self.nova = clients.NovaClient(username=username,
                                       api_key=password,
                                       project_id=tenant_name,
                                       auth_url=auth_url)
        self.neutron = clients.NeutronClient(username=username,
                                             password=password,
                                             tenant_name=tenant_name,
                                             auth_url=auth_url)

    def create_cluster(self):
        self.ng_id_map = self._create_node_group_templates()
        cl_tmpl_id = self._create_cluster_template()
        self.cluster_id = self._create_cluster(cl_tmpl_id)
        self._poll_cluster_status(self.cluster_id)

    @errormsg("Cluster scaling failed")
    def check_scale(self):
        scale_ops = []
        if self.testcase.get('scaling'):
            scale_ops = self.testcase['scaling']
        else:
            scale_path = os.path.join(self.template_path, 'scale.json')
            if os.path.exists(scale_path):
                with open(scale_path) as data:
                    scale_ops = json.load(data)

        body = {}
        for op in scale_ops:
            if op['operation'] == 'add':
                if 'add_node_groups' not in body:
                    body['add_node_groups'] = []
                body['add_node_groups'].append({
                    'node_group_template_id':
                    self.ng_id_map[op['node_group']],
                    'count': op['size'],
                    'name': utils.rand_name(op['node_group'])
                })
            if op['operation'] == 'resize':
                if 'resize_node_groups' not in body:
                    body['resize_node_groups'] = []
                body['resize_node_groups'].append({
                    'name': self.ng_name_map[op['node_group']],
                    'count': op['size']
                })

        if body:
            self.sahara.scale_cluster(self.cluster_id, body)
            self._poll_cluster_status(self.cluster_id)

    @errormsg("Create node group templates failed")
    def _create_node_group_templates(self):
        ng_id_map = {}
        floating_ip_pool = None
        if self.network['type'] == 'neutron':
            floating_ip_pool = self.neutron.get_network_id(
                self.network['public_network'])
        elif not self.network['auto_assignment_floating_ip']:
            floating_ip_pool = self.network['public_network']

        node_groups = []
        if self.testcase.get('node_group_templates'):
            for ng in self.testcase['node_group_templates']:
                node_groups.append(ng)
        else:
            templates_path = os.path.join(self.template_path,
                                          'node_group_template_*.json')
            for template_file in glob.glob(templates_path):
                with open(template_file) as data:
                    node_groups.append(json.load(data))

        for ng in node_groups:
            kwargs = dict(ng)
            kwargs.update(self.plugin_opts)
            kwargs['name'] = utils.rand_name(kwargs['name'])
            kwargs['floating_ip_pool'] = floating_ip_pool
            ng_id = self.__create_node_group_template(**kwargs)
            ng_id_map[ng['name']] = ng_id

        return ng_id_map

    @errormsg("Create cluster template failed")
    def _create_cluster_template(self):
        self.ng_name_map = {}
        template = None
        if self.testcase.get('cluster_template'):
            template = self.testcase['cluster_template']
        else:
            template_path = os.path.join(self.template_path,
                                         'cluster_template.json')
            with open(template_path) as data:
                template = json.load(data)

        kwargs = dict(template)
        ngs = kwargs['node_group_templates']
        del kwargs['node_group_templates']
        kwargs['node_groups'] = []
        for ng, count in ngs.items():
            ng_name = utils.rand_name(ng)
            self.ng_name_map[ng] = ng_name
            kwargs['node_groups'].append({
                'name': ng_name,
                'node_group_template_id': self.ng_id_map[ng],
                'count': count})

        kwargs.update(self.plugin_opts)
        kwargs['name'] = utils.rand_name(kwargs['name'])
        if self.network['type'] == 'neutron':
            kwargs['net_id'] = self.neutron.get_network_id(
                self.network['private_network'])

        return self.__create_cluster_template(**kwargs)

    @errormsg("Create cluster failed")
    def _create_cluster(self, cluster_template_id):
        if self.testcase.get('cluster'):
            kwargs = dict(self.testcase['cluster'])
        else:
            kwargs = {}  # default template

        kwargs.update(self.plugin_opts)
        kwargs['name'] = utils.rand_name(kwargs.get('name', 'test'))
        kwargs['cluster_template_id'] = cluster_template_id
        kwargs['default_image_id'] = self.nova.get_image_id(
            self.testcase['image'])

        return self.__create_cluster(**kwargs)

    def _poll_cluster_status(self, cluster_id):
        # TODO(sreshetniak): make timeout configurable
        with fixtures.Timeout(1800, gentle=True):
            while True:
                status = self.sahara.get_cluster_status(cluster_id)
                if status == 'Active':
                    break
                if status == 'Error':
                    raise exc.TempestException("Cluster in %s state" % status)
                time.sleep(3)

    # sahara client ops

    def __create_node_group_template(self, *args, **kwargs):
        id = self.sahara.create_node_group_template(*args, **kwargs)
        if not self.testcase['retain_resources']:
            self.addCleanup(self.sahara.delete_node_group_template, id)
        return id

    def __create_cluster_template(self, *args, **kwargs):
        id = self.sahara.create_cluster_template(*args, **kwargs)
        if not self.testcase['retain_resources']:
            self.addCleanup(self.sahara.delete_cluster_template, id)
        return id

    def __create_cluster(self, *args, **kwargs):
        id = self.sahara.create_cluster(*args, **kwargs)
        if not self.testcase['retain_resources']:
            self.addCleanup(self.sahara.delete_cluster, id)
        return id
