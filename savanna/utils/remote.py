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

import logging
import time

from eventlet import semaphore
from eventlet import timeout as e_timeout
from oslo.config import cfg
import paramiko

from savanna import context
from savanna import exceptions as ex
from savanna.openstack.common import excutils
from savanna.utils import crypto
from savanna.utils.openstack import nova
from savanna.utils import procutils


LOG = logging.getLogger(__name__)


remote_opts = [
    cfg.IntOpt('global_remote_threshold', default=100,
               help='Maximum number of remote operations that will '
                    'be running at the same time. Note that each '
                    'remote operation requires its own process to'
                    'run.'),
    cfg.IntOpt('cluster_remote_threshold', default=70,
               help='The same as global_remote_threshold, but for '
                    'a single cluster.'),
]

CONF = cfg.CONF
CONF.register_opts(remote_opts)

_ssh = None


def _connect(host, username, private_key):
    global _ssh

    if type(private_key) in [str, unicode]:
        private_key = crypto.to_paramiko_private_key(private_key)
    _ssh = paramiko.SSHClient()
    _ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    _ssh.connect(host, username=username, pkey=private_key)


def _cleanup():
    global _ssh
    _ssh.close()


def _read_paramimko_stream(recv_func):
    result = ''
    buf = recv_func(1024)
    while buf != '':
        result += buf
        buf = recv_func(1024)

    return result


def _execute_command(cmd, get_stderr=False, raise_when_error=True):
    global _ssh

    chan = _ssh.get_transport().open_session()
    chan.exec_command(cmd)

    # todo(dmitryme): that could hang if stderr buffer overflows
    stdout = _read_paramimko_stream(chan.recv)
    stderr = _read_paramimko_stream(chan.recv_stderr)

    ret_code = chan.recv_exit_status()

    if ret_code and raise_when_error:
        raise ex.RemoteCommandException(cmd=cmd, ret_code=ret_code,
                                        stdout=stdout, stderr=stderr)

    if get_stderr:
        return ret_code, stdout, stderr
    else:
        return ret_code, stdout


def _write_file(sftp, remote_file, data):
    fl = sftp.file(remote_file, 'w')
    fl.write(data)
    fl.close()


def _write_file_to(remote_file, data):
    global _ssh

    _write_file(_ssh.open_sftp(), remote_file, data)


def _write_files_to(files):
    global _ssh

    sftp = _ssh.open_sftp()

    for fl, data in files.iteritems():
        _write_file(sftp, fl, data)


def _read_file_from(remote_file):
    global _ssh

    fl = _ssh.open_sftp().file(remote_file, 'r')
    data = fl.read()
    fl.close()
    return data


def _replace_remote_string(remote_file, old_str, new_str):
    old_str = old_str.replace("\'", "\''")
    new_str = new_str.replace("\'", "\''")
    cmd = "sudo sed -i 's,%s,%s,g' %s" % (old_str, new_str, remote_file)
    _execute_command(cmd)


def _execute_on_vm_interactive(cmd, matcher):
    global _ssh

    buf = ''

    channel = _ssh.invoke_shell()
    try:
        channel.send(cmd + '\n')
        while not matcher.is_eof(buf):
            buf += channel.recv(4096)
            response = matcher.get_response(buf)
            if response is not None:
                channel.send(response + '\n')
                buf = ''
    finally:
        channel.close()


_global_remote_semaphore = None


def setup_remote():
    global _global_remote_semaphore
    _global_remote_semaphore = semaphore.Semaphore(
        CONF.global_remote_threshold)


def _acquire_remote_semaphore():
    context.current().remote_semaphore.acquire()
    _global_remote_semaphore.acquire()


def _release_remote_semaphore():
    _global_remote_semaphore.release()
    context.current().remote_semaphore.release()


class InstanceInteropHelper(object):
    def __init__(self, instance):
        self.instance = instance
        self.username = nova.get_node_group_image_username(
            self.instance.node_group)

    def __enter__(self):
        _acquire_remote_semaphore()
        try:
            self.bulk = BulkInstanceInteropHelper(self.instance, self.username)
            return self.bulk
        except Exception:
            with excutils.save_and_reraise_exception():
                _release_remote_semaphore()

    def __exit__(self, *exc_info):
        try:
            self.bulk.close()
        finally:
            _release_remote_semaphore()

    def _get_conn_params(self):
        return (self.instance.management_ip, self.username,
                self.instance.node_group.cluster.management_private_key)

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

    def _run_with_log(self, func, timeout, *args, **kwargs):
        start_time = time.time()
        try:
            with e_timeout.Timeout(timeout):
                return self._run(func, *args, **kwargs)
        finally:
            self._log_command('%s took %.1f seconds to complete' % (
                func.__name__, time.time() - start_time))

    def _run_s(self, func, timeout, *args, **kwargs):
        _acquire_remote_semaphore()
        try:
            return self._run_with_log(func, timeout, *args, **kwargs)
        finally:
            _release_remote_semaphore()

    def execute_command(self, cmd, get_stderr=False, raise_when_error=True,
                        timeout=300):
        """Execute specified command remotely using existing ssh connection.

        Return exit code, stdout data and stderr data of the executed command.
        """
        self._log_command('Executing "%s"' % cmd)
        return self._run_s(_execute_command, timeout, cmd, get_stderr,
                           raise_when_error)

    def write_file_to(self, remote_file, data, timeout=120):
        """Create remote file using existing ssh connection and write the given
        data to it.
        """
        self._log_command('Writing file "%s"' % remote_file)
        self._run_s(_write_file_to, timeout, remote_file, data)

    def write_files_to(self, files, timeout=120):
        """Copy file->data dictionary in a single ssh connection.
        """
        self._log_command('Writing files "%s"' % files.keys())
        self._run_s(_write_files_to, timeout, files)

    def read_file_from(self, remote_file, timeout=120):
        """Read remote file from the specified host and return given data."""
        self._log_command('Reading file "%s"' % remote_file)
        return self._run_s(_read_file_from, timeout, remote_file)

    def replace_remote_string(self, remote_file, old_str, new_str,
                              timeout=120):
        """Replaces strings in remote file using sed command."""
        self._log_command('In file "%s" replacing string "%s" '
                          'with "%s"' % (remote_file, old_str, new_str))
        self._run_s(_replace_remote_string, timeout, remote_file, old_str,
                    new_str)

    def execute_on_vm_interactive(self, cmd, matcher, timeout=1800):
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
        self._log_command('Executing interactively "%s"' % cmd)
        self._run_s(_execute_on_vm_interactive, timeout, cmd, matcher)

    def _log_command(self, str):
        LOG.debug('[%s] %s' % (self.instance.instance_name, str))


def get_remote(instance):
    return InstanceInteropHelper(instance)


class BulkInstanceInteropHelper(InstanceInteropHelper):
    def __init__(self, instance, username):
        self.instance = instance
        self.username = username
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

    def _run_s(self, func, timeout, *args, **kwargs):
        return self._run_with_log(func, timeout, *args, **kwargs)
