# Copyright (c) 2013 Mirantis Inc.
# Copyright (c) 2013 Hortonworks, Inc.
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

"""Helper methods for executing commands on nodes via SSH.

The main access point is method get_remote(instance), it returns
InstanceInteropHelper object which does the actual work. See the
class for the list of available methods.

It is a context manager, so it could be used with 'with' statement
like that:
with get_remote(instance) as r:
    r.execute_command(...)

Note that the module offloads the ssh calls to a child process.
It was implemented that way because we found no way to run paramiko
and eventlet together. The private high-level module methods are
implementations which are run in a separate process.
"""

import copy
import os
import shlex
import sys
import threading
import time

from eventlet.green import subprocess as e_subprocess
from eventlet import semaphore
from eventlet import timeout as e_timeout
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import uuidutils
import paramiko
import requests
from requests import adapters
import six

from sahara import context
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.service import trusts
from sahara.utils import crypto
from sahara.utils import network as net_utils
from sahara.utils.openstack import neutron
from sahara.utils import procutils
from sahara.utils import remote


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


ssh_config_options = [
    cfg.IntOpt(
        'ssh_timeout_common', default=300, min=1,
        help="Overrides timeout for common ssh operations, in seconds"),
    cfg.IntOpt(
        'ssh_timeout_interactive', default=1800, min=1,
        help="Overrides timeout for interactive ssh operations, in seconds"),
    cfg.IntOpt(
        'ssh_timeout_files', default=600, min=1,
        help="Overrides timeout for ssh operations with files, in seconds"),
]

CONF.register_opts(ssh_config_options)

_ssh = None
_proxy_ssh = None
_sessions = {}


INFRA = None

SSH_TIMEOUTS_MAPPING = {
    '_execute_command': 'ssh_timeout_common',
    '_execute_command_interactive': 'ssh_timeout_interactive'
}

_global_remote_semaphore = None


def _get_access_ip(instance):
    if CONF.proxy_command and CONF.proxy_command_use_internal_ip:
        return instance.internal_ip
    return instance.management_ip


def _default_timeout(func):
    timeout = SSH_TIMEOUTS_MAPPING.get(func.__name__, 'ssh_timeout_files')
    return getattr(CONF, timeout, CONF.ssh_timeout_common)


def _get_ssh_timeout(func, timeout):
    return timeout if timeout else _default_timeout(func)


def _connect(host, username, private_key, proxy_command=None,
             gateway_host=None, gateway_image_username=None):
    global _ssh
    global _proxy_ssh

    LOG.debug('Creating SSH connection')
    if isinstance(private_key, six.string_types):
        private_key = crypto.to_paramiko_private_key(private_key)

    _ssh = paramiko.SSHClient()
    _ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    proxy = None
    if proxy_command:
        LOG.debug('Creating proxy using command: {command}'.format(
            command=proxy_command))
        proxy = paramiko.ProxyCommand(proxy_command)

    if gateway_host:
        _proxy_ssh = paramiko.SSHClient()
        _proxy_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        LOG.debug('Connecting to proxy gateway at: {gateway}'.format(
            gateway=gateway_host))
        _proxy_ssh.connect(gateway_host, username=gateway_image_username,
                           pkey=private_key, sock=proxy)

        proxy = _proxy_ssh.get_transport().open_session()
        proxy.exec_command("nc {0} 22".format(host))

    _ssh.connect(host, username=username, pkey=private_key, sock=proxy)


def _cleanup():
    global _ssh
    global _proxy_ssh

    _ssh.close()
    if _proxy_ssh:
        _proxy_ssh.close()


def _read_paramimko_stream(recv_func):
    result = b''
    buf = recv_func(1024)
    while buf != b'':
        result += buf
        buf = recv_func(1024)

    return result


def _escape_quotes(command):
    command = command.replace('\\', '\\\\')
    command = command.replace('"', '\\"')
    command = command.replace('`', '\\`')
    return command


def _execute_command(cmd, run_as_root=False, get_stderr=False,
                     raise_when_error=True):
    global _ssh

    chan = _ssh.get_transport().open_session()
    if run_as_root:
        chan.exec_command('sudo bash -c "%s"' % _escape_quotes(cmd))
    else:
        chan.exec_command(cmd)

    # TODO(dmitryme): that could hang if stderr buffer overflows
    stdout = _read_paramimko_stream(chan.recv)
    stderr = _read_paramimko_stream(chan.recv_stderr)

    if type(stdout) == bytes:
        stdout = stdout.decode('utf-8')

    if type(stderr) == bytes:
        stderr = stderr.decode('utf-8')

    ret_code = chan.recv_exit_status()

    if ret_code and raise_when_error:
        raise ex.RemoteCommandException(cmd=cmd, ret_code=ret_code,
                                        stdout=stdout, stderr=stderr)

    if get_stderr:
        return ret_code, stdout, stderr
    else:
        return ret_code, stdout


def _execute_command_interactive(cmd, run_as_root=False):
    global _ssh

    chan = _ssh.get_transport().open_session()
    if run_as_root:
        chan.exec_command('sudo bash -c "%s"' % _escape_quotes(cmd))
    else:
        chan.exec_command(cmd)

    _proxy_shell(chan)

    _ssh.close()


def _proxy_shell(chan):
    def readall():
        while True:
            d = sys.stdin.read(1)
            if not d or chan.exit_status_ready():
                break
            chan.send(d)

    reader = threading.Thread(target=readall)
    reader.start()

    while True:
        data = chan.recv(256)
        if not data or chan.exit_status_ready():
            break
        sys.stdout.write(data)
        sys.stdout.flush()


def _get_http_client(host, port, proxy_command=None, gateway_host=None,
                     gateway_username=None, gateway_private_key=None):
    global _sessions

    _http_session = _sessions.get((host, port), None)
    LOG.debug('Cached HTTP session for {host}:{port} is {session}'.format(
        host=host, port=port, session=_http_session))
    if not _http_session:
        if gateway_host:
            _http_session = _get_proxy_gateway_http_session(
                gateway_host, gateway_username,
                gateway_private_key, host, port, proxy_command)
            LOG.debug('Created ssh proxied HTTP session for {host}:{port}'
                      .format(host=host, port=port))
        elif proxy_command:
            # can return a new session here because it actually uses
            # the same adapter (and same connection pools) for a given
            # host and port tuple
            _http_session = _get_proxied_http_session(
                proxy_command, host, port=port)
            LOG.debug('Created proxied HTTP session for {host}:{port}'
                      .format(host=host, port=port))
        else:
            # need to cache the sessions that are not proxied through
            # HTTPRemoteWrapper so that a new session with a new HTTPAdapter
            # and associated pools is not recreated for each HTTP invocation
            _http_session = requests.Session()
            LOG.debug('Created standard HTTP session for {host}:{port}'
                      .format(host=host, port=port))

            adapter = requests.adapters.HTTPAdapter()
            for prefix in ['http://', 'https://']:
                _http_session.mount(prefix + '%s:%s' % (host, port),
                                    adapter)

        LOG.debug('Caching session {session} for {host}:{port}'
                  .format(session=_http_session, host=host, port=port))
        _sessions[(host, port)] = _http_session

    return _http_session


def _write_fl(sftp, remote_file, data):
    try:
        write_data = paramiko.py3compat.StringIO(data)
    except TypeError:
        write_data = paramiko.py3compat.BytesIO(data)

    sftp.putfo(write_data, remote_file)


def _append_fl(sftp, remote_file, data):
    fl = sftp.file(remote_file, 'a')
    fl.write(data)
    fl.close()


def _write_file(sftp, remote_file, data, run_as_root):
    if run_as_root:
        temp_file = 'temp-file-%s' % uuidutils.generate_uuid()
        _write_fl(sftp, temp_file, data)
        _execute_command(
            'mv %s %s' % (temp_file, remote_file), run_as_root=True)
    else:
        _write_fl(sftp, remote_file, data)


def _append_file(sftp, remote_file, data, run_as_root):
    if run_as_root:
        temp_file = 'temp-file-%s' % uuidutils.generate_uuid()
        _write_fl(sftp, temp_file, data)
        _execute_command(
            'cat %s >> %s' % (temp_file, remote_file), run_as_root=True)
        _execute_command('rm -f %s' % temp_file)
    else:
        _append_fl(sftp, remote_file, data)


def _prepend_file(sftp, remote_file, data, run_as_root):
    if run_as_root:
        temp_file = 'temp-file-%s' % uuidutils.generate_uuid()
        temp_remote_file = 'temp-remote-file-%s' % uuidutils.generate_uuid()
        _write_fl(sftp, temp_file, data)
        _execute_command(
            'cat %s > %s' % (remote_file, temp_remote_file))
        _execute_command(
            'cat %s %s > %s' % (
                temp_file, temp_remote_file, remote_file), run_as_root=True)
        _execute_command('rm -f %s %s' % (temp_file, temp_remote_file))


def _write_file_to(remote_file, data, run_as_root=False):
    global _ssh

    _write_file(_ssh.open_sftp(), remote_file, data, run_as_root)


def _write_files_to(files, run_as_root=False):
    global _ssh

    sftp = _ssh.open_sftp()

    for fl, data in six.iteritems(files):
        _write_file(sftp, fl, data, run_as_root)


def _append_to_file(remote_file, data, run_as_root=False):
    global _ssh

    _append_file(_ssh.open_sftp(), remote_file, data, run_as_root)


def _append_to_files(files, run_as_root=False):
    global _ssh

    sftp = _ssh.open_sftp()

    for fl, data in six.iteritems(files):
        _append_file(sftp, fl, data, run_as_root)


def _prepend_to_file(remote_file, data, run_as_root=False):
    global _ssh

    _prepend_file(_ssh.open_sftp(), remote_file, data, run_as_root)


def _prepend_to_files(files, run_as_root=False):
    global _ssh

    sftp = _ssh.open_sftp()

    for fl, data in six.iteritems(files):
        _prepend_file(sftp, fl, data, run_as_root)


def _read_file(sftp, remote_file):
    fl = sftp.file(remote_file, 'r')
    data = fl.read()
    fl.close()
    try:
        return data.decode('utf-8')
    except Exception:
        return data


def _read_file_from(remote_file, run_as_root=False):
    global _ssh

    fl = remote_file
    if run_as_root:
        fl = 'temp-file-%s' % (uuidutils.generate_uuid())
        _execute_command('cp %s %s' % (remote_file, fl), run_as_root=True)

    try:
        return _read_file(_ssh.open_sftp(), fl)
    except IOError:
        LOG.error("Can't read file {filename}".format(filename=remote_file))
        raise
    finally:
        if run_as_root:
            _execute_command(
                'rm %s' % fl, run_as_root=True, raise_when_error=False)


def _get_python_to_execute():
    try:
        _execute_command('python3 --version')
    except Exception:
        _execute_command('python2 --version')
        return 'python2'
    return 'python3'


def _get_os_distrib():
    python_version = _get_python_to_execute()
    return _execute_command(
        ('printf "import platform\nprint(platform.linux_distribution('
         'full_distribution_name=0)[0])" | {}'.format(python_version)),
        run_as_root=False)[1].lower().strip()


def _get_os_version():
    python_version = _get_python_to_execute()
    return _execute_command(
        ('printf "import platform\nprint(platform.linux_distribution()[1])"'
         ' | {}'.format(python_version)), run_as_root=False)[1].strip()


def _install_packages(packages):
    distrib = _get_os_distrib()
    if distrib == 'ubuntu':
        cmd = 'RUNLEVEL=1 apt-get install -y %(pkgs)s'
    elif distrib == 'fedora':
        fversion = _get_os_version()
        if fversion >= 22:
            cmd = 'dnf install -y %(pkgs)s'
        else:
            cmd = 'yum install -y %(pkgs)s'
    elif distrib in ('redhat', 'centos'):
        cmd = 'yum install -y %(pkgs)s'
    else:
        raise ex.NotImplementedException(
            _('Package Installation'),
            _('%(fmt)s is not implemented for OS %(distrib)s') % {
                'fmt': '%s', 'distrib': distrib})
    cmd = cmd % {'pkgs': ' '.join(packages)}
    _execute_command(cmd, run_as_root=True)


def _update_repository():
    distrib = _get_os_distrib()
    if distrib == 'ubuntu':
        cmd = 'apt-get update'
    elif distrib == 'fedora':
        fversion = _get_os_version()
        if fversion >= 22:
            cmd = 'dnf clean all'
        else:
            cmd = 'yum clean all'
    elif distrib in ('redhat', 'centos'):
        cmd = 'yum clean all'
    else:
        raise ex.NotImplementedException(
            _('Repository Update'),
            _('%(fmt)s is not implemented for OS %(distrib)s') % {
                'fmt': '%s', 'distrib': distrib})
    _execute_command(cmd, run_as_root=True)


def _replace_remote_string(remote_file, old_str, new_str):
    old_str = old_str.replace("\'", "\''")
    new_str = new_str.replace("\'", "\''")
    cmd = "sudo sed -i 's,%s,%s,g' %s" % (old_str, new_str, remote_file)
    _execute_command(cmd)


def _replace_remote_line(remote_file, old_line_with_start_string, new_line):
    search_string = old_line_with_start_string.replace("\'", "\''")
    cmd = ("sudo sed -i  's/^%s.*/%s/' %s" % (search_string,
                                              new_line, remote_file))
    _execute_command(cmd)


def _execute_on_vm_interactive(cmd, matcher):
    global _ssh

    buf = ''

    channel = _ssh.invoke_shell()
    LOG.debug('Channel is {channel}'.format(channel=channel))
    try:
        LOG.debug('Sending cmd {command}'.format(command=cmd))
        channel.send(cmd + '\n')
        while not matcher.is_eof(buf):
            buf += channel.recv(4096)
            response = matcher.get_response(buf)
            if response is not None:
                channel.send(response + '\n')
                buf = ''
    finally:
        LOG.debug('Closing channel')
        channel.close()


def _acquire_remote_semaphore():
    context.current().remote_semaphore.acquire()
    _global_remote_semaphore.acquire()


def _release_remote_semaphore():
    _global_remote_semaphore.release()
    context.current().remote_semaphore.release()


def _get_proxied_http_session(proxy_command, host, port=None):
    session = requests.Session()

    adapter = ProxiedHTTPAdapter(
        _simple_exec_func(shlex.split(proxy_command)), host, port)
    session.mount('http://{0}:{1}'.format(host, adapter.port), adapter)

    return session


def _get_proxy_gateway_http_session(gateway_host, gateway_username,
                                    gateway_private_key, host, port=None,
                                    proxy_command=None):
    session = requests.Session()
    adapter = ProxiedHTTPAdapter(
        _proxy_gateway_func(gateway_host, gateway_username,
                            gateway_private_key, host,
                            port, proxy_command),
        host, port)
    session.mount('http://{0}:{1}'.format(host, port), adapter)

    return session


def _simple_exec_func(cmd):
    def func():
        return e_subprocess.Popen(cmd,
                                  stdin=e_subprocess.PIPE,
                                  stdout=e_subprocess.PIPE,
                                  stderr=e_subprocess.PIPE)

    return func


def _proxy_gateway_func(gateway_host, gateway_username,
                        gateway_private_key, host,
                        port, proxy_command):
    def func():
        proc = procutils.start_subprocess()

        try:
            conn_params = (gateway_host, gateway_username, gateway_private_key,
                           proxy_command, None, None)
            procutils.run_in_subprocess(proc, _connect, conn_params)
            cmd = "nc {host} {port}".format(host=host, port=port)
            procutils.run_in_subprocess(
                proc, _execute_command_interactive, (cmd,), interactive=True)
            return proc
        except Exception:
            with excutils.save_and_reraise_exception():
                procutils.shutdown_subprocess(proc, _cleanup)

    return func


class ProxiedHTTPAdapter(adapters.HTTPAdapter):
    def __init__(self, create_process_func, host, port):
        super(ProxiedHTTPAdapter, self).__init__()
        LOG.debug('HTTP adapter created for {host}:{port}'.format(host=host,
                                                                  port=port))
        self.create_process_func = create_process_func
        self.port = port
        self.host = host

    def get_connection(self, url, proxies=None):
        pool_conn = (
            super(ProxiedHTTPAdapter, self).get_connection(url, proxies))
        if hasattr(pool_conn, '_get_conn'):
            http_conn = pool_conn._get_conn()
            if http_conn.sock is None:
                if hasattr(http_conn, 'connect'):
                    sock = self._connect()
                    LOG.debug('HTTP connection {connection} getting new '
                              'netcat socket {socket}'.format(
                                  connection=http_conn, socket=sock))
                    http_conn.sock = sock
            else:
                if hasattr(http_conn.sock, 'is_netcat_socket'):
                    LOG.debug('Pooled http connection has existing '
                              'netcat socket. resetting pipe')
                    http_conn.sock.reset()

            pool_conn._put_conn(http_conn)

        return pool_conn

    def close(self):
        LOG.debug('Closing HTTP adapter for {host}:{port}'
                  .format(host=self.host, port=self.port))
        super(ProxiedHTTPAdapter, self).close()

    def _connect(self):
        LOG.debug('Returning netcat socket for {host}:{port}'
                  .format(host=self.host, port=self.port))
        rootwrap_command = CONF.rootwrap_command if CONF.use_rootwrap else ''
        return NetcatSocket(self.create_process_func, rootwrap_command)


class NetcatSocket(object):

    def _create_process(self):
        self.process = self.create_process_func()

    def __init__(self, create_process_func, rootwrap_command=None):
        self.create_process_func = create_process_func
        self.rootwrap_command = rootwrap_command
        self._create_process()

    def send(self, content):
        try:
            self.process.stdin.write(content)
            self.process.stdin.flush()
        except IOError as e:
            raise ex.SystemError(e)
        return len(content)

    def sendall(self, content):
        return self.send(content)

    def makefile(self, mode, *arg):
        if mode.startswith('r'):
            return self.process.stdout
        if mode.startswith('w'):
            return self.process.stdin
        raise ex.IncorrectStateError(_("Unknown file mode %s") % mode)

    def recv(self, size):
        try:
            return os.read(self.process.stdout.fileno(), size)
        except IOError as e:
            raise ex.SystemError(e)

    def _terminate(self):
        if self.rootwrap_command:
            os.system('{0} kill {1}'.format(self.rootwrap_command,  # nosec
                                            self.process.pid))
        else:
            self.process.terminate()

    def close(self):
        LOG.debug('Socket close called')
        self._terminate()

    def settimeout(self, timeout):
        pass

    def fileno(self):
        return self.process.stdin.fileno()

    def is_netcat_socket(self):
        return True

    def reset(self):
        self._terminate()
        self._create_process()


class InstanceInteropHelper(remote.Remote):
    def __init__(self, instance):
        self.instance = instance

    def __enter__(self):
        _acquire_remote_semaphore()
        try:
            self.bulk = BulkInstanceInteropHelper(self.instance)
            return self.bulk
        except Exception:
            with excutils.save_and_reraise_exception():
                _release_remote_semaphore()

    def __exit__(self, *exc_info):
        try:
            self.bulk.close()
        finally:
            _release_remote_semaphore()

    def get_neutron_info(self, instance=None):
        if not instance:
            instance = self.instance
        neutron_info = dict()
        neutron_info['network'] = instance.cluster.neutron_management_network
        ctx = context.current()
        neutron_info['token'] = context.get_auth_token()
        neutron_info['tenant'] = ctx.tenant_name
        neutron_info['host'] = _get_access_ip(instance)

        log_info = copy.deepcopy(neutron_info)
        del log_info['token']
        LOG.debug('Returning neutron info: {info}'.format(info=log_info))
        return neutron_info

    def _build_proxy_command(self, command, instance=None, port=None,
                             info=None, rootwrap_command=None):
        # Accepted keywords in the proxy command template:
        # {host}, {port}, {tenant_id}, {network_id}, {router_id}
        keywords = {}

        if not info:
            info = self.get_neutron_info(instance)
        keywords['tenant_id'] = context.current().tenant_id
        keywords['network_id'] = info['network']

        # Query Neutron only if needed
        if '{router_id}' in command:
            auth = trusts.get_os_admin_auth_plugin(instance.cluster)
            client = neutron.NeutronClient(info['network'], info['token'],
                                           info['tenant'], auth=auth)
            keywords['router_id'] = client.get_router()

        keywords['host'] = _get_access_ip(instance)
        keywords['port'] = port

        try:
            command = command.format(**keywords)
        except KeyError as e:
            LOG.error('Invalid keyword in proxy_command: {result}'.format(
                result=e))
            # Do not give more details to the end-user
            raise ex.SystemError('Misconfiguration')
        if rootwrap_command:
            command = '{0} {1}'.format(rootwrap_command, command)
        return command

    def _get_conn_params(self):
        host_ng = self.instance.node_group
        cluster = host_ng.cluster
        access_instance = self.instance
        proxy_gateway_node = cluster.get_proxy_gateway_node()

        gateway_host = None
        gateway_image_username = None
        if proxy_gateway_node and not host_ng.is_proxy_gateway:

            # tmckay-fp in other words, if we are going to connect
            # through the proxy instead of the node we are actually
            # trying to reach

            # okay, the node group that supplies the proxy gateway
            # must have fps, but if a proxy is used the other
            # nodes are not required to have an fp.

            # so, this instance is assumed not to have a floating
            # ip and we are going to get to it through the proxy
            access_instance = proxy_gateway_node
            gateway_host = proxy_gateway_node.management_ip
            ng = proxy_gateway_node.node_group
            gateway_image_username = ng.image_username

        proxy_command = None
        if CONF.proxy_command:
            # Build a session through a user-defined socket
            proxy_command = CONF.proxy_command

        # tmckay-fp we have the node_group for the instance right here
        # okay, this test here whether access_instance.management_ip is an
        # fp -- just compare to internal?
        # in the neutron case, we check the node group for the
        # access_instance and look for fp
        elif CONF.use_namespaces and not net_utils.has_floating_ip(
                access_instance):
            # Build a session through a netcat socket in the Neutron namespace
            proxy_command = (
                'ip netns exec qrouter-{router_id} nc {host} {port}')
        # proxy_command is currently a template, turn it into a real command
        # i.e. dereference {host}, {port}, etc.
        if proxy_command:
            rootwrap = CONF.rootwrap_command if CONF.use_rootwrap else ''
            proxy_command = self._build_proxy_command(
                proxy_command, instance=access_instance, port=22,
                info=None, rootwrap_command=rootwrap)

        host_ip = _get_access_ip(self.instance)

        return (host_ip,
                host_ng.image_username,
                cluster.management_private_key,
                proxy_command,
                gateway_host,
                gateway_image_username)

    def _run(self, func, *args, **kwargs):
        proc = procutils.start_subprocess()

        try:
            procutils.run_in_subprocess(proc, _connect,
                                        self._get_conn_params())
            return procutils.run_in_subprocess(proc, func, args, kwargs)
        except Exception:
            with excutils.save_and_reraise_exception():
                procutils.shutdown_subprocess(proc, _cleanup)
        finally:
            procutils.shutdown_subprocess(proc, _cleanup)

    def _run_with_log(self, func, timeout, description, *args, **kwargs):
        start_time = time.time()

        try:
            with e_timeout.Timeout(timeout,
                                   ex.TimeoutException(timeout,
                                                       op_name=description)):
                return self._run(func, *args, **kwargs)
        finally:
            self._log_command('"%s" took %.1f seconds to complete' % (
                description, time.time() - start_time))

    def _run_s(self, func, timeout, description, *args, **kwargs):
        timeout = _get_ssh_timeout(func, timeout)
        _acquire_remote_semaphore()
        try:
            return self._run_with_log(func, timeout,
                                      description, *args, **kwargs)
        finally:
            _release_remote_semaphore()

    def get_http_client(self, port, info=None):
        self._log_command('Retrieving HTTP session for {0}:{1}'.format(
            _get_access_ip(self.instance), port))

        host_ng = self.instance.node_group
        cluster = host_ng.cluster
        access_instance = self.instance
        access_port = port
        proxy_gateway_node = cluster.get_proxy_gateway_node()

        gateway_host = None
        gateway_username = None
        gateway_private_key = None
        if proxy_gateway_node and not host_ng.is_proxy_gateway:
            access_instance = proxy_gateway_node
            access_port = 22
            gateway_host = proxy_gateway_node.management_ip
            gateway_username = proxy_gateway_node.node_group.image_username
            gateway_private_key = cluster.management_private_key

        proxy_command = None
        if CONF.proxy_command:
            # Build a session through a user-defined socket
            proxy_command = CONF.proxy_command

        # tmckay-fp again we can check the node group for the instance
        # what are the implications for nova here? None.
        # This is a test on whether access_instance has a floating_ip
        # in the neutron case, we check the node group for the
        # access_instance and look for fp
        elif (CONF.use_namespaces and not net_utils.has_floating_ip(
                access_instance)):
            # need neutron info
            if not info:
                info = self.get_neutron_info(access_instance)
            # Build a session through a netcat socket in the Neutron namespace
            proxy_command = (
                'ip netns exec qrouter-{router_id} nc {host} {port}')
        # proxy_command is currently a template, turn it into a real command
        # i.e. dereference {host}, {port}, etc.
        if proxy_command:
            rootwrap = CONF.rootwrap_command if CONF.use_rootwrap else ''
            proxy_command = self._build_proxy_command(
                proxy_command, instance=access_instance, port=access_port,
                info=info, rootwrap_command=rootwrap)

        return _get_http_client(_get_access_ip(self.instance), port,
                                proxy_command, gateway_host,
                                gateway_username,
                                gateway_private_key)

    def close_http_session(self, port):
        global _sessions

        host = _get_access_ip(self.instance)
        self._log_command(_("Closing HTTP session for %(host)s:%(port)s") % {
                          'host': host, 'port': port})

        session = _sessions.get((host, port), None)
        if session is None:
            raise ex.NotFoundException(
                {'host': host, 'port': port},
                _('Session for %(host)s:%(port)s not cached'))

        session.close()
        del _sessions[(host, port)]

    def execute_command(self, cmd, run_as_root=False, get_stderr=False,
                        raise_when_error=True, timeout=None):
        description = _('Executing "%s"') % cmd
        self._log_command(description)
        return self._run_s(_execute_command, timeout, description,
                           cmd, run_as_root, get_stderr, raise_when_error)

    def write_file_to(self, remote_file, data, run_as_root=False,
                      timeout=None):
        description = _('Writing file "%s"') % remote_file
        self._log_command(description)
        self._run_s(_write_file_to, timeout, description,
                    remote_file, data, run_as_root)

    def write_files_to(self, files, run_as_root=False, timeout=None):
        description = _('Writing files "%s"') % list(files)
        self._log_command(description)
        self._run_s(_write_files_to, timeout, description, files, run_as_root)

    def append_to_file(self, r_file, data, run_as_root=False, timeout=None):
        description = _('Appending to file "%s"') % r_file
        self._log_command(description)
        self._run_s(_append_to_file, timeout, description,
                    r_file, data, run_as_root)

    def append_to_files(self, files, run_as_root=False, timeout=None):
        description = _('Appending to files "%s"') % list(files)
        self._log_command(description)
        self._run_s(_append_to_files, timeout, description, files, run_as_root)

    def prepend_to_file(self, r_file, data, run_as_root=False, timeout=None):
        description = _('Prepending to file "%s"') % r_file
        self._log_command(description)
        self._run_s(_prepend_to_file, timeout, description,
                    r_file, data, run_as_root)

    def read_file_from(self, remote_file, run_as_root=False, timeout=None):
        description = _('Reading file "%s"') % remote_file
        self._log_command(description)
        return self._run_s(_read_file_from, timeout, description,
                           remote_file, run_as_root)

    def get_python_version(self, timeout=None):
        return self._run_s(
            _get_python_to_execute, timeout, "get_python_version")

    def get_os_distrib(self, timeout=None):
        return self._run_s(_get_os_distrib, timeout, "get_os_distrib")

    def get_os_version(self, timeout=None):
        return self._run_s(_get_os_version, timeout, "get_os_version")

    def install_packages(self, packages, timeout=None):
        description = _('Installing packages "%s"') % list(packages)
        self._log_command(description)
        self._run_s(_install_packages, timeout, description, packages)

    def update_repository(self, timeout=None):
        description = _('Updating repository')
        self._log_command(description)
        self._run_s(_update_repository, timeout, description)

    def replace_remote_string(self, remote_file, old_str, new_str,
                              timeout=None):
        description = _('In file "%(file)s" replacing string '
                        '"%(old_string)s" with "%(new_string)s"') % {
            "file": remote_file,
            "old_string": old_str, "new_string": new_str}

        self._log_command(description)
        self._run_s(_replace_remote_string, timeout, description,
                    remote_file, old_str, new_str)

    def replace_remote_line(self, remote_file,
                            old_line_with_start_string,
                            new_line, timeout=None):
        description = _('In file "%(file)s" replacing line'
                        ' beginning with string '
                        '"%(old_line_with_start_string)s"'
                        ' with "%(new_line)s"') % {
            "file": remote_file,
            "old_line_with_start_string": old_line_with_start_string,
            "new_line": new_line}

        self._log_command(description)
        self._run_s(_replace_remote_line, timeout, description,
                    remote_file, old_line_with_start_string, new_line)

    def execute_on_vm_interactive(self, cmd, matcher, timeout=None):
        """Runs given command and responds to prompts.

        'cmd' is a command to execute.

        'matcher' is an object which provides responses on command's
        prompts. It should have two methods implemented:
         * get_response(buf) - returns response on prompt if it is
             found  in 'buf' string, which is a part of command output.
             If no prompt is found, the method should return None.
         * is_eof(buf) - returns True if current 'buf' indicates that
             the command is finished. False should be returned
             otherwise.
        """
        description = _('Executing interactively "%s"') % cmd
        self._log_command(description)
        self._run_s(_execute_on_vm_interactive, timeout,
                    description, cmd, matcher)

    def _log_command(self, str):
        with context.set_current_instance_id(self.instance.instance_id):
            LOG.debug(str)


class BulkInstanceInteropHelper(InstanceInteropHelper):
    def __init__(self, instance):
        super(BulkInstanceInteropHelper, self).__init__(instance)
        self.proc = procutils.start_subprocess()
        try:
            procutils.run_in_subprocess(self.proc, _connect,
                                        self._get_conn_params())
        except Exception:
            with excutils.save_and_reraise_exception():
                procutils.shutdown_subprocess(self.proc, _cleanup)

    def close(self):
        procutils.shutdown_subprocess(self.proc, _cleanup)

    def _run(self, func, *args, **kwargs):
        return procutils.run_in_subprocess(self.proc, func, args, kwargs)

    def _run_s(self, func, timeout, description, *args, **kwargs):
        timeout = _get_ssh_timeout(func, timeout)
        return self._run_with_log(func, timeout, description, *args, **kwargs)


class SshRemoteDriver(remote.RemoteDriver):
    def get_type_and_version(self):
        return "ssh.1.0"

    def setup_remote(self, engine):
        global _global_remote_semaphore
        global INFRA

        _global_remote_semaphore = semaphore.Semaphore(
            CONF.global_remote_threshold)

        INFRA = engine

    def get_remote(self, instance):
        return InstanceInteropHelper(instance)

    def get_userdata_template(self):
        # SSH does not need any instance customization
        return ""
