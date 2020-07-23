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


import shlex
from unittest import mock

import testtools

from sahara import exceptions as ex
from sahara.tests.unit import base
from sahara.utils import ssh_remote


class TestEscapeQuotes(testtools.TestCase):
    def test_escape_quotes(self):
        s = ssh_remote._escape_quotes('echo "\\"Hello, world!\\""')
        self.assertEqual(r'echo \"\\\"Hello, world!\\\"\"', s)


class TestGetOsDistrib(testtools.TestCase):
    @mock.patch('sahara.utils.ssh_remote._execute_command',
                return_value=[1, 'Ubuntu'])
    @mock.patch('sahara.utils.ssh_remote._get_python_to_execute',
                return_value='python3')
    def test_get_os_distrib(self, python, p_execute_command):
        d = ssh_remote._get_os_distrib()
        p_execute_command.assert_called_once_with(
            ('printf "import platform\nprint(platform.linux_distribution('
             'full_distribution_name=0)[0])" | python3'),
            run_as_root=False)
        self.assertEqual('ubuntu', d)


class TestInstallPackages(testtools.TestCase):
    @mock.patch('sahara.utils.ssh_remote._get_os_version')
    @mock.patch('sahara.utils.ssh_remote._get_os_distrib')
    @mock.patch('sahara.utils.ssh_remote._execute_command')
    def test_install_packages(self, p_execute_command, p_get_os_distrib,
                              p_get_os_version):
        packages = ('git', 'emacs', 'tree')

        # test ubuntu
        p_get_os_distrib.return_value = 'ubuntu'
        ssh_remote._install_packages(packages)
        p_execute_command.assert_called_with(
            'RUNLEVEL=1 apt-get install -y git emacs tree', run_as_root=True)

        # test centos
        p_get_os_distrib.return_value = 'centos'
        ssh_remote._install_packages(packages)
        p_execute_command.assert_called_with(
            'yum install -y git emacs tree',
            run_as_root=True)

        # test fedora < 22
        p_get_os_distrib.return_value = 'fedora'
        p_get_os_version.return_value = 20
        ssh_remote._install_packages(packages)
        p_execute_command.assert_called_with(
            'yum install -y git emacs tree',
            run_as_root=True)

        # test fedora >=22
        p_get_os_distrib.return_value = 'fedora'
        p_get_os_version.return_value = 23
        ssh_remote._install_packages(packages)
        p_execute_command.assert_called_with(
            'dnf install -y git emacs tree',
            run_as_root=True)

        # test redhat
        p_get_os_distrib.return_value = 'redhat'
        ssh_remote._install_packages(packages)
        p_execute_command.assert_called_with(
            'yum install -y git emacs tree',
            run_as_root=True)

    @mock.patch('sahara.utils.ssh_remote._get_os_distrib',
                return_value='windows me')
    def test_install_packages_bad(self, p_get_os_distrib):
        with testtools.ExpectedException(
                ex.NotImplementedException,
                'Package Installation is not implemented for OS windows me.*'):
            ssh_remote._install_packages(('git', 'emacs', 'tree'))


class TestUpdateRepository(testtools.TestCase):
    @mock.patch('sahara.utils.ssh_remote._get_os_version')
    @mock.patch('sahara.utils.ssh_remote._get_os_distrib')
    @mock.patch('sahara.utils.ssh_remote._execute_command')
    def test_update_repository(self, p_execute_command, p_get_os_distrib,
                               p_get_os_version):
        # test ubuntu
        p_get_os_distrib.return_value = 'ubuntu'
        ssh_remote._update_repository()
        p_execute_command.assert_called_with(
            'apt-get update', run_as_root=True)

        # test centos
        p_get_os_distrib.return_value = 'centos'
        ssh_remote._update_repository()
        p_execute_command.assert_called_with(
            'yum clean all', run_as_root=True)

        # test fedora < 22
        p_get_os_distrib.return_value = 'fedora'
        p_get_os_version.return_value = 20
        ssh_remote._update_repository()
        p_execute_command.assert_called_with(
            'yum clean all', run_as_root=True)

        # test fedora >=22
        p_get_os_distrib.return_value = 'fedora'
        p_get_os_version.return_value = 23
        ssh_remote._update_repository()
        p_execute_command.assert_called_with(
            'dnf clean all', run_as_root=True)
        # test redhat
        p_get_os_distrib.return_value = 'redhat'
        ssh_remote._update_repository()
        p_execute_command.assert_called_with(
            'yum clean all', run_as_root=True)

    @mock.patch('sahara.utils.ssh_remote._get_os_distrib',
                return_value='windows me')
    def test_update_repository_bad(self, p_get_os_distrib):
        with testtools.ExpectedException(
                ex.NotImplementedException,
                'Repository Update is not implemented for OS windows me.*'):
            ssh_remote._update_repository()


class FakeCluster(object):
    def __init__(self, priv_key):
        self.management_private_key = priv_key
        self.neutron_management_network = 'network1'

    def has_proxy_gateway(self):
        return False

    def get_proxy_gateway_node(self):
        return None


class FakeNodeGroup(object):
    def __init__(self, user, priv_key):
        self.image_username = user
        self.cluster = FakeCluster(priv_key)
        self.floating_ip_pool = 'public'


class FakeInstance(object):
    def __init__(self, inst_name, inst_id, management_ip, internal_ip, user,
                 priv_key):
        self.instance_name = inst_name
        self.instance_id = inst_id
        self.management_ip = management_ip
        self.internal_ip = internal_ip
        self.node_group = FakeNodeGroup(user, priv_key)

    @property
    def cluster(self):
        return self.node_group.cluster


class TestInstanceInteropHelper(base.SaharaTestCase):
    def setUp(self):
        super(TestInstanceInteropHelper, self).setUp()

        p_sma = mock.patch('sahara.utils.ssh_remote._acquire_remote_semaphore')
        p_sma.start()
        p_smr = mock.patch('sahara.utils.ssh_remote._release_remote_semaphore')
        p_smr.start()

        p_neutron_router = mock.patch(
            'sahara.utils.openstack.neutron.NeutronClient.get_router',
            return_value='fakerouter')
        p_neutron_router.start()
        # During tests subprocesses are not used (because _sahara-subprocess
        # is not installed in /bin and Mock objects cannot be pickled).
        p_start_subp = mock.patch('sahara.utils.procutils.start_subprocess',
                                  return_value=42)
        p_start_subp.start()
        p_run_subp = mock.patch('sahara.utils.procutils.run_in_subprocess')
        self.run_in_subprocess = p_run_subp.start()
        p_shut_subp = mock.patch('sahara.utils.procutils.shutdown_subprocess')
        p_shut_subp.start()

        self.patchers = [p_sma, p_smr, p_neutron_router, p_start_subp,
                         p_run_subp, p_shut_subp]

    def tearDown(self):
        for patcher in self.patchers:
            patcher.stop()
        super(TestInstanceInteropHelper, self).tearDown()

    def setup_context(self, username="test_user", tenant_id="tenant_1",
                      token="test_auth_token", tenant_name='test_tenant',
                      **kwargs):
        service_catalog = '''[
            { "type": "network",
              "endpoints": [ { "region": "RegionOne",
                               "publicURL": "http://localhost/" } ] } ]'''
        super(TestInstanceInteropHelper, self).setup_context(
            username=username, tenant_id=tenant_id, token=token,
            tenant_name=tenant_name, service_catalog=service_catalog, **kwargs)

    # When use_floating_ips=True, no proxy should be used: _connect is called
    # with proxy=None and ProxiedHTTPAdapter is not used.
    @mock.patch('sahara.utils.ssh_remote.ProxiedHTTPAdapter')
    def test_use_floating_ips(self, p_adapter):
        self.override_config('use_floating_ips', True)

        instance = FakeInstance('inst1', '123', '10.0.0.1', '10.0.0.1',
                                'user1', 'key1')
        remote = ssh_remote.InstanceInteropHelper(instance)

        # Test SSH
        remote.execute_command('/bin/true')
        self.run_in_subprocess.assert_any_call(
            42, ssh_remote._connect, ('10.0.0.1', 'user1', 'key1',
                                      None, None, None))
        # Test HTTP
        remote.get_http_client(8080)
        self.assertFalse(p_adapter.called)

    # When use_floating_ips=False and use_namespaces=True, a netcat socket
    # created with 'ip netns exec qrouter-...' should be used to access
    # instances.
    @mock.patch("sahara.service.trusts.get_os_admin_auth_plugin")
    @mock.patch("sahara.utils.openstack.keystone.token_auth")
    @mock.patch('sahara.utils.ssh_remote._simple_exec_func')
    @mock.patch('sahara.utils.ssh_remote.ProxiedHTTPAdapter')
    def test_use_namespaces(self, p_adapter, p_simple_exec_func, token_auth,
                            use_os_admin):
        self.override_config('use_floating_ips', False)
        self.override_config('use_namespaces', True)

        instance = FakeInstance('inst2', '123', '10.0.0.2', '10.0.0.2',
                                'user2', 'key2')
        remote = ssh_remote.InstanceInteropHelper(instance)

        # Test SSH
        remote.execute_command('/bin/true')
        self.run_in_subprocess.assert_any_call(
            42, ssh_remote._connect,
            ('10.0.0.2', 'user2', 'key2',
             'ip netns exec qrouter-fakerouter nc 10.0.0.2 22', None, None))
        # Test HTTP
        remote.get_http_client(8080)
        p_adapter.assert_called_once_with(
            p_simple_exec_func(),
            '10.0.0.2', 8080)
        p_simple_exec_func.assert_any_call(
            shlex.split('ip netns exec qrouter-fakerouter nc 10.0.0.2 8080'))

    # When proxy_command is set, a user-defined netcat socket should be used to
    # access instances.
    @mock.patch('sahara.utils.ssh_remote._simple_exec_func')
    @mock.patch('sahara.utils.ssh_remote.ProxiedHTTPAdapter')
    def test_proxy_command(self, p_adapter, p_simple_exec_func):
        self.override_config('proxy_command', 'ssh fakerelay nc {host} {port}')

        instance = FakeInstance('inst3', '123', '10.0.0.3', '10.0.0.3',
                                'user3', 'key3')
        remote = ssh_remote.InstanceInteropHelper(instance)

        # Test SSH
        remote.execute_command('/bin/true')
        self.run_in_subprocess.assert_any_call(
            42, ssh_remote._connect,
            ('10.0.0.3', 'user3', 'key3', 'ssh fakerelay nc 10.0.0.3 22',
             None, None))
        # Test HTTP
        remote.get_http_client(8080)
        p_adapter.assert_called_once_with(
            p_simple_exec_func(), '10.0.0.3', 8080)
        p_simple_exec_func.assert_any_call(
            shlex.split('ssh fakerelay nc 10.0.0.3 8080'))

    @mock.patch('sahara.utils.ssh_remote._simple_exec_func')
    @mock.patch('sahara.utils.ssh_remote.ProxiedHTTPAdapter')
    def test_proxy_command_internal_ip(self, p_adapter, p_simple_exec_func):
        self.override_config('proxy_command', 'ssh fakerelay nc {host} {port}')
        self.override_config('proxy_command_use_internal_ip', True)

        instance = FakeInstance('inst3', '123', '10.0.0.3', '10.0.0.4',
                                'user3', 'key3')
        remote = ssh_remote.InstanceInteropHelper(instance)

        # Test SSH
        remote.execute_command('/bin/true')
        self.run_in_subprocess.assert_any_call(
            42, ssh_remote._connect,
            ('10.0.0.4', 'user3', 'key3', 'ssh fakerelay nc 10.0.0.4 22',
             None, None))
        # Test HTTP
        remote.get_http_client(8080)
        p_adapter.assert_called_once_with(
            p_simple_exec_func(), '10.0.0.4', 8080)
        p_simple_exec_func.assert_any_call(
            shlex.split('ssh fakerelay nc 10.0.0.4 8080'))

    def test_proxy_command_bad(self):
        self.override_config('proxy_command', '{bad_kw} nc {host} {port}')

        instance = FakeInstance('inst4', '123', '10.0.0.4', '10.0.0.4',
                                'user4', 'key4')
        remote = ssh_remote.InstanceInteropHelper(instance)

        # Test SSH
        self.assertRaises(ex.SystemError, remote.execute_command, '/bin/true')
        # Test HTTP
        self.assertRaises(ex.SystemError, remote.get_http_client, 8080)

    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._run_s')
    def test_get_os_distrib(self, p_run_s):
        instance = FakeInstance('inst4', '123', '10.0.0.4', '10.0.0.4',
                                'user4', 'key4')
        remote = ssh_remote.InstanceInteropHelper(instance)

        remote.get_os_distrib()
        p_run_s.assert_called_with(ssh_remote._get_os_distrib,
                                   None, "get_os_distrib")

    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._run_s')
    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._log_command')
    def test_install_packages(self, p_log_command, p_run_s):
        instance = FakeInstance('inst5', '123', '10.0.0.5', '10.0.0.5',
                                'user5', 'key5')
        remote = ssh_remote.InstanceInteropHelper(instance)

        packages = ['pkg1', 'pkg2']
        remote.install_packages(packages)
        description = 'Installing packages "%s"' % list(packages)
        p_run_s.assert_called_once_with(
            ssh_remote._install_packages, None, description, packages)

        p_log_command.assert_called_with(description)

    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._run_s')
    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._log_command')
    def test_update_repository(self, p_log_command, p_run_s):
        instance = FakeInstance('inst6', '123', '10.0.0.6', '10.0.0.6',
                                'user6', 'key6')
        remote = ssh_remote.InstanceInteropHelper(instance)

        remote.update_repository()
        p_run_s.assert_called_once_with(ssh_remote._update_repository,
                                        None, 'Updating repository')

        p_log_command.assert_called_with('Updating repository')

    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._run_s')
    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._log_command')
    def test_write_file_to(self, p_log_command, p_run_s):
        instance = FakeInstance('inst7', '123', '10.0.0.7', '10.0.0.7',
                                'user7', 'key7')
        remote = ssh_remote.InstanceInteropHelper(instance)
        description = 'Writing file "file"'

        remote.write_file_to("file", "data")
        p_run_s.assert_called_once_with(ssh_remote._write_file_to, None,
                                        description, "file", "data", False)

        p_log_command.assert_called_with(description)

    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._run_s')
    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._log_command')
    def test_write_files_to(self, p_log_command, p_run_s):
        instance = FakeInstance('inst8', '123', '10.0.0.8', '10.0.0.8',
                                'user8', 'key8')
        remote = ssh_remote.InstanceInteropHelper(instance)
        description = 'Writing files "[\'file\']"'

        remote.write_files_to({"file": "data"})
        p_run_s.assert_called_once_with(ssh_remote._write_files_to, None,
                                        description, {"file": "data"}, False)

        p_log_command.assert_called_with(description)

    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._run_s')
    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._log_command')
    def test_append_to_file(self, p_log_command, p_run_s):
        instance = FakeInstance('inst9', '123', '10.0.0.9', '10.0.0.9',
                                'user9', 'key9')
        remote = ssh_remote.InstanceInteropHelper(instance)
        description = 'Appending to file "file"'

        remote.append_to_file("file", "data")
        p_run_s.assert_called_once_with(ssh_remote._append_to_file, None,
                                        description, "file", "data", False)

        p_log_command.assert_called_with(description)

    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._run_s')
    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._log_command')
    def test_append_to_files(self, p_log_command, p_run_s):
        instance = FakeInstance('inst10', '123',
                                '10.0.0.10', '10.0.0.10', 'user10', 'key10')
        remote = ssh_remote.InstanceInteropHelper(instance)
        description = 'Appending to files "[\'file\']"'

        remote.append_to_files({"file": "data"})
        p_run_s.assert_called_once_with(ssh_remote._append_to_files, None,
                                        description, {"file": "data"}, False)

        p_log_command.assert_called_with(description)

    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._run_s')
    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._log_command')
    def test_read_file_from(self, p_log_command, p_run_s):
        instance = FakeInstance('inst11', '123',
                                '10.0.0.11', '10.0.0.11', 'user11', 'key11')
        remote = ssh_remote.InstanceInteropHelper(instance)
        description = 'Reading file "file"'

        remote.read_file_from("file")
        p_run_s.assert_called_once_with(ssh_remote._read_file_from, None,
                                        description, "file", False)

        p_log_command.assert_called_with(description)

    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._run_s')
    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._log_command')
    def test_replace_remote_string(self, p_log_command, p_run_s):
        instance = FakeInstance('inst12', '123',
                                '10.0.0.12', '10.0.0.12', 'user12', 'key12')
        remote = ssh_remote.InstanceInteropHelper(instance)
        description = 'In file "file" replacing string "str1" with "str2"'

        remote.replace_remote_string("file", "str1", "str2")
        p_run_s.assert_called_once_with(ssh_remote._replace_remote_string,
                                        None, description, "file", "str1",
                                                                   "str2")

        p_log_command.assert_called_with(description)

    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._run_s')
    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._log_command')
    def test_replace_remote_line(self, p_log_command, p_run_s):
        instance = FakeInstance('inst13', '123',
                                '10.0.0.13', '10.0.0.13', 'user13', 'key13')
        remote = ssh_remote.InstanceInteropHelper(instance)
        description = ('In file "file" replacing line beginning with string '
                       '"str" with "newline"')

        remote.replace_remote_line("file", "str", "newline")
        p_run_s.assert_called_once_with(ssh_remote._replace_remote_line,
                                        None, description, "file", "str",
                                                                   "newline")

        p_log_command.assert_called_with(description)

    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._run_s')
    @mock.patch('sahara.utils.ssh_remote.InstanceInteropHelper._log_command')
    def test_execute_on_vm_interactive(self, p_log_command, p_run_s):
        instance = FakeInstance('inst14', '123',
                                '10.0.0.14', '10.0.0.14', 'user14', 'key14')
        remote = ssh_remote.InstanceInteropHelper(instance)
        description = 'Executing interactively "factor 42"'

        remote.execute_on_vm_interactive("factor 42", None)
        p_run_s.assert_called_once_with(ssh_remote._execute_on_vm_interactive,
                                        None, description, "factor 42", None)

        p_log_command(description)
