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
import logging
import os
import sys
import time
import traceback

import fixtures
from oslo_serialization import jsonutils as json
from oslo_utils import timeutils
import prettytable
import six
from tempest_lib import base
from tempest_lib.common import ssh as connection
from tempest_lib import exceptions as exc

from sahara.tests.scenario import clients
from sahara.tests.scenario import timeouts
from sahara.tests.scenario import utils
from sahara.utils import crypto as ssh

logger = logging.getLogger('swiftclient')
logger.setLevel(logging.CRITICAL)

DEFAULT_TEMPLATES_PATH = (
    'sahara/tests/scenario/templates/%(plugin_name)s/%(hadoop_version)s')
CHECK_OK_STATUS = "OK"
CHECK_FAILED_STATUS = "FAILED"
CLUSTER_STATUS_ACTIVE = "Active"
CLUSTER_STATUS_ERROR = "Error"


def track_result(check_name, exit_with_error=True):
    def decorator(fct):
        @functools.wraps(fct)
        def wrapper(self, *args, **kwargs):
            test_info = {
                'check_name': check_name,
                'status': CHECK_OK_STATUS,
                'duration': None,
                'traceback': None
            }
            self._results.append(test_info)
            started_at = timeutils.utcnow()
            try:
                return fct(self, *args, **kwargs)
            except Exception:
                test_info['status'] = CHECK_FAILED_STATUS
                test_info['traceback'] = traceback.format_exception(
                    *sys.exc_info())
                if exit_with_error:
                    raise
            finally:
                test_time = timeutils.utcnow() - started_at
                test_info['duration'] = test_time.seconds
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
        timeouts.Defaults.init_defaults(self.testcase)
        self.testcase['ssh_username'] = self.sahara.sahara_client.images.get(
            self.nova.get_image_id(self.testcase['image'])).username
        self.key = self.testcase.get('key_name')
        if self.key is None:
            self.private_key, self.public_key = ssh.generate_key_pair()
            self.key_name = self.__create_keypair()
        # save the private key if retain_resources is specified
        # (useful for debugging purposes)
        if self.testcase['retain_resources'] or self.key is None:
            with open(self.key_name + '.key', 'a') as private_key_file:
                private_key_file.write(self.private_key)
        self.plugin_opts = {
            'plugin_name': self.testcase['plugin_name'],
            'hadoop_version': self.testcase['plugin_version']
        }
        self.template_path = DEFAULT_TEMPLATES_PATH % self.plugin_opts
        self.cinder = True
        self.proxy_ng_name = False
        self.proxy = False

    def _init_clients(self):
        username = self.credentials['os_username']
        password = self.credentials['os_password']
        tenant_name = self.credentials['os_tenant']
        auth_url = self.credentials['os_auth_url']
        sahara_service_type = self.credentials['sahara_service_type']
        sahara_url = self.credentials['sahara_url']

        session = clients.get_session(auth_url, username, password,
                                      tenant_name,
                                      self.credentials['ssl_verify'],
                                      self.credentials['ssl_cert'])

        self.sahara = clients.SaharaClient(session=session,
                                           service_type=sahara_service_type,
                                           sahara_url=sahara_url)
        self.nova = clients.NovaClient(session=session)
        self.neutron = clients.NeutronClient(session=session)
        # swiftclient doesn't support keystone sessions
        self.swift = clients.SwiftClient(
            authurl=auth_url,
            user=username,
            key=password,
            insecure=not self.credentials['ssl_verify'],
            cacert=self.credentials['ssl_cert'],
            tenant_name=tenant_name)

    def create_cluster(self):
        self.cluster_id = self.sahara.get_cluster_id(
            self.testcase.get('existing_cluster'))
        self.ng_id_map = {}
        if self.cluster_id is None:
            self.ng_id_map = self._create_node_group_templates()
            cl_tmpl_id = self._create_cluster_template()
            self.cluster_id = self._create_cluster(cl_tmpl_id)
        elif self.key is None:
            self.cinder = False
        self._poll_cluster_status_tracked(self.cluster_id)
        cluster = self.sahara.get_cluster(self.cluster_id, show_progress=True)
        if self.proxy_ng_name:
            for ng in cluster.node_groups:
                if ng['name'] == self.proxy_ng_name:
                    self.proxy = ng['instances'][0]['management_ip']

        self.check_cinder()
        if not getattr(cluster, "provision_progress", None):
            return
        self._check_event_logs(cluster)

    @track_result("Check transient")
    def check_transient(self):
        with fixtures.Timeout(
                timeouts.Defaults.instance.timeout_check_transient,
                gentle=True):
            while True:
                if self.sahara.is_resource_deleted(
                        self.sahara.get_cluster_status, self.cluster_id):
                    break
                time.sleep(5)

    def _inject_datasources_data(self, arg, input_url, output_url):
        return arg.format(
            input_datasource=input_url, output_datasource=output_url)

    def _put_io_data_to_configs(self, configs, input_id, output_id):
        input_url, output_url = None, None
        if input_id is not None:
            input_url = self.sahara.get_datasource(
                data_source_id=input_id).url
        if output_id is not None:
            output_url = self.sahara.get_datasource(
                data_source_id=output_id).url
        pl = lambda x: self._inject_datasources_data(x, input_url, output_url)
        args = list(map(pl, configs.get('args', [])))
        configs['args'] = args
        return configs

    def _prepare_job_running(self, job):
        input_id, output_id = self._create_datasources(job)
        main_libs, additional_libs = self._create_job_binaries(job)
        job_id = self._create_job(job['type'], main_libs, additional_libs)
        configs = self._parse_job_configs(job)
        configs = self._put_io_data_to_configs(
            configs, input_id, output_id)
        return [job_id, input_id, output_id, configs]

    @track_result("Check EDP jobs", False)
    def check_run_jobs(self):
        batching = self.testcase.get('edp_batching',
                                     len(self.testcase['edp_jobs_flow']))
        batching_size = batching
        jobs = self.testcase.get('edp_jobs_flow', [])

        pre_exec = []
        for job in jobs:
            pre_exec.append(self._prepare_job_running(job))
            batching -= 1
            if not batching:
                self._job_batching(pre_exec)
                pre_exec = []
                batching = batching_size

    def _job_batching(self, pre_exec):
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
                url = self._create_hdfs_data(location, ds.get('hdfs_username',
                                                              'oozie'))
            if ds['type'] == 'maprfs':
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
        try:
            with fixtures.Timeout(
                    timeouts.Defaults.instance.timeout_poll_jobs_status,
                    gentle=True):
                success = False
                polling_ids = list(exec_ids)
                while not success:
                    current_ids = list(polling_ids)
                    success = True
                    for exec_id in polling_ids:
                        status = self.sahara.get_job_status(exec_id)
                        if status not in ['FAILED', 'KILLED', 'DONEWITHERROR',
                                          "SUCCEEDED"]:
                            success = False
                        else:
                            current_ids.remove(exec_id)
                    polling_ids = list(current_ids)
                    time.sleep(5)
        finally:
            report = []
            for exec_id in exec_ids:
                status = self.sahara.get_job_status(exec_id)
                if status != "SUCCEEDED":
                    info = self.sahara.get_job_info(exec_id)
                    report.append("Job with id={id}, name={name}, "
                                  "type={type} has status "
                                  "{status}".format(id=exec_id,
                                                    name=info.name,
                                                    type=info.type,
                                                    status=status))
            if report:
                self.fail("\n".join(report))

    def _create_swift_data(self, source=None):
        container = self._get_swift_container()
        path = utils.rand_name('test')
        data = None
        if source:
            with open(source) as source_fd:
                data = source_fd.read()

        self.__upload_to_container(container, path, data)

        return 'swift://%s.sahara/%s' % (container, path)

    def _create_hdfs_data(self, source, hdfs_username):

        def to_hex_present(string):
            return "".join(map(lambda x: hex(ord(x)).replace("0x", "\\x"),
                               string))

        if 'user' in source:
            return source
        hdfs_dir = utils.rand_name("/user/%s/data" % hdfs_username)
        inst_ip = self._get_nodes_with_process()[0]["management_ip"]
        self._run_command_on_node(
            inst_ip,
            "sudo su - -c \"hdfs dfs -mkdir -p %(path)s \" %(user)s" % {
                "path": hdfs_dir, "user": hdfs_username})
        hdfs_filepath = utils.rand_name(hdfs_dir + "/file")
        with open(source) as source_fd:
            data = source_fd.read()
        self._run_command_on_node(
            inst_ip,
            ("echo -e \"%(data)s\" | sudo su - -c \"hdfs dfs"
             " -put - %(path)s\" %(user)s") % {
                 "data": to_hex_present(data),
                 "path": hdfs_filepath,
                 "user": hdfs_username})
        return hdfs_filepath

    def _create_internal_db_data(self, source):
        with open(source) as source_fd:
            data = source_fd.read()
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
        ng_before_scale = self.sahara.get_cluster(self.cluster_id).node_groups
        if self.testcase.get('scaling'):
            scale_ops = self.testcase['scaling']
        else:
            scale_path = os.path.join(self.template_path, 'scale.json')
            if os.path.exists(scale_path):
                with open(scale_path) as data:
                    scale_ops = json.load(data)

        body = {}
        for op in scale_ops:
            node_scale = op['node_group']
            if op['operation'] == 'add':
                if 'add_node_groups' not in body:
                    body['add_node_groups'] = []
                body['add_node_groups'].append({
                    'node_group_template_id':
                    self.ng_id_map.get(node_scale,
                                       self.sahara.get_node_group_template_id(
                                           node_scale)),
                    'count': op['size'],
                    'name': utils.rand_name(node_scale)
                })
            if op['operation'] == 'resize':
                if 'resize_node_groups' not in body:
                    body['resize_node_groups'] = []
                body['resize_node_groups'].append({
                    'name': self.ng_name_map.get(
                        node_scale,
                        self.sahara.get_node_group_template_id(node_scale)),
                    'count': op['size']
                })

        if body:
            self.sahara.scale_cluster(self.cluster_id, body)
            self._poll_cluster_status(self.cluster_id)
            ng_after_scale = self.sahara.get_cluster(
                self.cluster_id).node_groups
            self._validate_scaling(ng_after_scale,
                                   self._get_expected_count_of_nodes(
                                       ng_before_scale, body))

    def _validate_scaling(self, after, expected_count):
        for (key, value) in six.iteritems(expected_count):
            ng = {}
            for after_ng in after:
                if after_ng['name'] == key:
                    ng = after_ng
                    break
            self.assertEqual(value, ng.get('count', 0))

    def _get_expected_count_of_nodes(self, before, body):
        expected_mapper = {}
        for ng in before:
            expected_mapper[ng['name']] = ng['count']
        for ng in body.get('add_node_groups', []):
            expected_mapper[ng['name']] = ng['count']
        for ng in body.get('resize_node_groups', []):
            expected_mapper[ng['name']] = ng['count']
        return expected_mapper

    @track_result("Check cinder volumes")
    def check_cinder(self):
        if not self._get_node_list_with_volumes() or not self.cinder:
            print("All tests for Cinder were skipped")
            return
        for node_with_volumes in self._get_node_list_with_volumes():
            volume_count_on_node = int(self._run_command_on_node(
                node_with_volumes['node_ip'],
                'mount | grep %s | wc -l' %
                node_with_volumes['volume_mount_prefix']
            ))
            self.assertEqual(
                node_with_volumes['volume_count'], volume_count_on_node,
                'Some volumes were not mounted to node.\n'
                'Expected count of mounted volumes to node is %s.\n'
                'Actual count of mounted volumes to node is %s.'
                % (node_with_volumes['volume_count'], volume_count_on_node)
            )

    def _get_node_list_with_volumes(self):
        node_groups = self.sahara.get_cluster(self.cluster_id).node_groups
        node_list_with_volumes = []
        for node_group in node_groups:
            if node_group['volumes_per_node'] != 0:
                for instance in node_group['instances']:
                    node_list_with_volumes.append({
                        'node_ip': instance['management_ip'],
                        'volume_count': node_group['volumes_per_node'],
                        'volume_mount_prefix':
                            node_group['volume_mount_prefix']
                    })
        return node_list_with_volumes

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

        check_indirect_access = False
        for ng in node_groups:
            if ng.get('is_proxy_gateway'):
                check_indirect_access = True

        for ng in node_groups:
            kwargs = dict(ng)
            kwargs.update(self.plugin_opts)
            kwargs['flavor_id'] = self._get_flavor_id(kwargs['flavor'])
            del kwargs['flavor']
            kwargs['name'] = utils.rand_name(kwargs['name'])
            if (not kwargs.get('is_proxy_gateway',
                               False)) and (check_indirect_access):
                kwargs['floating_ip_pool'] = None
                self.proxy_ng_name = kwargs['name']
            else:
                kwargs['floating_ip_pool'] = floating_ip_pool
            ng_id = self.__create_node_group_template(**kwargs)
            ng_id_map[ng['name']] = ng_id
        return ng_id_map

    @track_result("Set flavor")
    def _get_flavor_id(self, flavor):
        if isinstance(flavor, str):
            return self.nova.get_flavor_id(flavor)
        else:
            flavor_id = self.nova.create_flavor(flavor).id
            self.addCleanup(self.nova.delete_flavor, flavor_id)
            return flavor_id

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

    @track_result("Check event logs")
    def _check_event_logs(self, cluster):
        invalid_steps = []
        if cluster.is_transient:
            # skip event log testing
            return

        for step in cluster.provision_progress:
            if not step['successful']:
                invalid_steps.append(step)

        if len(invalid_steps) > 0:
            invalid_steps_info = "\n".join(six.text_type(e)
                                           for e in invalid_steps)
            steps_info = "\n".join(six.text_type(e)
                                   for e in cluster.provision_progress)
            raise exc.TempestException(
                "Issues with event log work: "
                "\n Incomplete steps: \n\n {invalid_steps}"
                "\n All steps: \n\n {steps}".format(
                    steps=steps_info,
                    invalid_steps=invalid_steps_info))

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
        kwargs['user_keypair_id'] = self.key_name

        return self.__create_cluster(**kwargs)

    @track_result("Check cluster state")
    def _poll_cluster_status_tracked(self, cluster_id):
        self._poll_cluster_status(cluster_id)

    def _poll_cluster_status(self, cluster_id):
        with fixtures.Timeout(
                timeouts.Defaults.instance.timeout_poll_cluster_status,
                gentle=True):
            while True:
                status = self.sahara.get_cluster_status(cluster_id)
                if status == CLUSTER_STATUS_ACTIVE:
                    break
                if status == CLUSTER_STATUS_ERROR:
                    raise exc.TempestException("Cluster in %s state" % status)
                time.sleep(3)

    def _run_command_on_node(self, node_ip, command):
        host_ip = node_ip
        if self.proxy:
            host_ip = self.proxy
            command = "ssh %s %s" % (node_ip, command)
        ssh_session = connection.Client(host_ip, self.testcase['ssh_username'],
                                        pkey=self.private_key)
        return ssh_session.exec_command(command)

    def _get_nodes_with_process(self, process=None):
        nodegroups = self.sahara.get_cluster(self.cluster_id).node_groups
        nodes_with_process = []
        for nodegroup in nodegroups:
            if not process or process in nodegroup['node_processes']:
                nodes_with_process.extend(nodegroup['instances'])
        return nodes_with_process

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

    def __create_keypair(self):
        key = utils.rand_name('scenario_key')
        self.nova.nova_client.keypairs.create(key,
                                              public_key=self.public_key)
        if not self.testcase['retain_resources']:
            self.addCleanup(self.nova.delete_keypair, key)
        return key

    def tearDown(self):
        tbs = []
        table = prettytable.PrettyTable(["Check", "Status", "Duration, s"])
        table.align["Check"] = "l"
        for check in self._results:
            table.add_row(
                [check['check_name'], check['status'], check['duration']])
            if check['status'] == CHECK_FAILED_STATUS:
                tbs.extend(check['traceback'])
                tbs.append("")
        print("Results of testing plugin", self.plugin_opts['plugin_name'],
              self.plugin_opts['hadoop_version'])
        print(table)
        print("\n".join(tbs), file=sys.stderr)

        super(BaseTestCase, self).tearDown()

        test_failed = any([c['status'] == CHECK_FAILED_STATUS
                           for c in self._results])
        if test_failed:
            self.fail("Scenario tests failed")
