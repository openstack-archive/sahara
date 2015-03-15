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
import logging
import os
import sys
import time
import traceback

import fixtures
import prettytable
import six
from tempest_lib import base
from tempest_lib import exceptions as exc

from sahara.tests.scenario import clients
from sahara.tests.scenario import utils


logger = logging.getLogger('swiftclient')
logger.setLevel(logging.CRITICAL)

DEFAULT_TEMPLATES_PATH = (
    'sahara/tests/scenario/templates/%(plugin_name)s/%(hadoop_version)s')
CHECK_OK_STATUS = "OK"
CHECK_FAILED_STATUS = "FAILED"


def track_result(check_name, exit_with_error=True):
    def decorator(fct):
        @functools.wraps(fct)
        def wrapper(self, *args, **kwargs):
            test_info = {
                'check_name': check_name,
                'status': CHECK_OK_STATUS,
                'traceback': None
            }
            self._results.append(test_info)
            try:
                return fct(self, *args, **kwargs)
            except Exception:
                test_info['status'] = CHECK_FAILED_STATUS
                test_info['traceback'] = traceback.format_exception(
                    *sys.exc_info())
                if exit_with_error:
                    raise
        return wrapper
    return decorator


class BaseTestCase(base.BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(BaseTestCase, cls).setUpClass()
        cls.network = None
        cls.credentials = None
        cls.testcase = None
        cls._results = []

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

        self.swift = clients.SwiftClient(authurl=auth_url,
                                         user=username,
                                         key=password,
                                         tenant_name=tenant_name)

    def create_cluster(self):
        self.ng_id_map = self._create_node_group_templates()
        cl_tmpl_id = self._create_cluster_template()
        self.cluster_id = self._create_cluster(cl_tmpl_id)
        self._poll_cluster_status(self.cluster_id)

    @track_result("Check transient")
    def check_transient(self):
        # TODO(sreshetniak): make timeout configurable
        with fixtures.Timeout(300, gentle=True):
            while True:
                if self.sahara.is_resource_deleted(
                        self.sahara.get_cluster_status, self.cluster_id):
                    break
                time.sleep(5)

    @track_result("Check EDP jobs", False)
    def check_run_jobs(self):
        jobs = {}
        if self.testcase['edp_jobs_flow']:
            jobs = self.testcase['edp_jobs_flow']
        else:
            jobs = []

        pre_exec = []
        for job in jobs:
            input_id, output_id = self._create_datasources(job)
            main_libs, additional_libs = self._create_job_binaries(job)
            job_id = self._create_job(job['type'], main_libs, additional_libs)
            configs = self._parse_job_configs(job)
            pre_exec.append([job_id, input_id, output_id, configs])

        job_exec_ids = []
        for job_exec in pre_exec:
            job_exec_ids.append(self._run_job(*job_exec))

        self._poll_jobs_status(job_exec_ids)

    def _create_datasources(self, job):
        def create(ds, name):
            location = ds.get('source', None)
            if not location:
                location = utils.rand_name(ds['destination'])
            if ds['type'] == 'swift':
                url = self._create_swift_data(location)
            if ds['type'] == 'hdfs':
                url = location
            return self.__create_datasource(
                name=utils.rand_name(name),
                description='',
                data_source_type=ds['type'], url=url,
                credential_user=self.credentials['os_username'],
                credential_pass=self.credentials['os_password'])

        input_id, output_id = None, None
        if job.get('input_datasource'):
            ds = job['input_datasource']
            input_id = create(ds, 'input')

        if job.get('output_datasource'):
            ds = job['output_datasource']
            output_id = create(ds, 'output')

        return input_id, output_id

    def _create_job_binaries(self, job):
        main_libs = []
        additional_libs = []
        if job.get('main_lib'):
            main_libs.append(self._create_job_binary(job['main_lib']))
        for add_lib in job.get('additional_libs', []):
            lib_id = self._create_job_binary(add_lib)
            additional_libs.append(lib_id)

        return main_libs, additional_libs

    def _create_job_binary(self, job_binary):
        url = None
        extra = {}
        if job_binary['type'] == 'swift':
            url = self._create_swift_data(job_binary['source'])
            extra['user'] = self.credentials['os_username']
            extra['password'] = self.credentials['os_password']
        if job_binary['type'] == 'database':
            url = self._create_internal_db_data(job_binary['source'])

        job_binary_name = '%s-%s' % (
            utils.rand_name('test'), os.path.basename(job_binary['source']))
        return self.__create_job_binary(job_binary_name, url, '', extra)

    def _create_job(self, type, mains, libs):
        return self.__create_job(utils.rand_name('test'), type, mains,
                                 libs, '')

    def _parse_job_configs(self, job):
        configs = {}
        if job.get('configs'):
            configs['configs'] = {}
            for param, value in six.iteritems(job['configs']):
                configs['configs'][param] = str(value)
        if job.get('args'):
            configs['args'] = map(str, job['args'])
        return configs

    def _run_job(self, job_id, input_id, output_id, configs):
        return self.__run_job(job_id, self.cluster_id, input_id, output_id,
                              configs)

    def _poll_jobs_status(self, exec_ids):
        # TODO(sreshetniak): make timeout configurable
        with fixtures.Timeout(1800, gentle=True):
            success = False
            while not success:
                success = True
                for exec_id in exec_ids:
                    status = self.sahara.get_job_status(exec_id)
                    if status in ['FAILED', 'KILLED', 'DONEWITHERROR']:
                        self.fail("Job %s in %s status" % (exec_id, status))
                    if status != 'SUCCEEDED':
                        success = False

                time.sleep(5)

    def _create_swift_data(self, source=None):
        container = self._get_swift_container()
        path = utils.rand_name('test')
        data = None
        if source:
            data = open(source).read()

        self.__upload_to_container(container, path, data)

        return 'swift://%s.sahara/%s' % (container, path)

    def _create_internal_db_data(self, source):
        data = open(source).read()
        id = self.__create_internal_db_data(utils.rand_name('test'), data)
        return 'internal-db://%s' % id

    def _get_swift_container(self):
        if not getattr(self, '__swift_container', None):
            self.__swift_container = self.__create_container(
                utils.rand_name('sahara-tests'))
        return self.__swift_container

    @track_result("Cluster scaling", False)
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

    @track_result("Create node group templates")
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

    @track_result("Create cluster template")
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

    @track_result("Create cluster")
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

    # client ops

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

    def __create_datasource(self, *args, **kwargs):
        id = self.sahara.create_datasource(*args, **kwargs)
        if not self.testcase['retain_resources']:
            self.addCleanup(self.sahara.delete_datasource, id)
        return id

    def __create_internal_db_data(self, *args, **kwargs):
        id = self.sahara.create_job_binary_internal(*args, **kwargs)
        if not self.testcase['retain_resources']:
            self.addCleanup(self.sahara.delete_job_binary_internal, id)
        return id

    def __create_job_binary(self, *args, **kwargs):
        id = self.sahara.create_job_binary(*args, **kwargs)
        if not self.testcase['retain_resources']:
            self.addCleanup(self.sahara.delete_job_binary, id)
        return id

    def __create_job(self, *args, **kwargs):
        id = self.sahara.create_job(*args, **kwargs)
        if not self.testcase['retain_resources']:
            self.addCleanup(self.sahara.delete_job, id)
        return id

    def __run_job(self, *args, **kwargs):
        id = self.sahara.run_job(*args, **kwargs)
        if not self.testcase['retain_resources']:
            self.addCleanup(self.sahara.delete_job_execution, id)
        return id

    def __create_container(self, container_name):
        self.swift.create_container(container_name)
        if not self.testcase['retain_resources']:
            self.addCleanup(self.swift.delete_container, container_name)
        return container_name

    def __upload_to_container(self, container_name, object_name, data=None):
        if data:
            self.swift.upload_data(container_name, object_name, data)
        if not self.testcase['retain_resources']:
            self.addCleanup(self.swift.delete_object, container_name,
                            object_name)

    def tearDown(self):
        tbs = []
        table = prettytable.PrettyTable(["Check", "Status"])
        table.align["Check"] = "l"
        for check in self._results:
            table.add_row([check['check_name'], check['status']])
            if check['status'] == CHECK_FAILED_STATUS:
                tbs.extend(check['traceback'])
                tbs.append("")
        print(table)
        print("\n".join(tbs), file=sys.stderr)

        super(BaseTestCase, self).tearDown()

        test_failed = any([c['status'] == CHECK_FAILED_STATUS
                           for c in self._results])
        if test_failed:
            self.fail("Scenario tests failed")
