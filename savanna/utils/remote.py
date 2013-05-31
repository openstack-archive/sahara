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

import functools
import paramiko


def setup_ssh_connection(host, username, private_key):
    """Setup SSH connection to the host using username and private key."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=username, pkey=private_key)

    return ssh


def execute_command(ssh_connection, cmd):
    """Execute specified command remotely using existing ssh connection.

    Return exit code and stdout data of the executed command.
    """
    try:
        chan = ssh_connection.get_transport().open_session()
        chan.exec_command(cmd)
        retcode = chan.recv_exit_status()
        buf = ''
        while chan.recv_ready():
            buf += chan.recv(1024)
        return retcode, buf
    finally:
        ssh_connection.close()


def write_file_to(ssh_connection, remote_file, data):
    """Create remote file using existing ssh connection and write the given
    data to it.
    """
    try:
        sftp = ssh_connection.open_sftp()
        fl = sftp.file(remote_file, 'w')
        fl.write(data)
        fl.close()
    finally:
        ssh_connection.close()


def read_file_from(ssh_connection, remote_file):
    """Read remote file from the specified host and return given data."""
    try:
        sftp = ssh_connection.open_sftp()
        fl = sftp.file(remote_file, 'r')
        data = fl.read()
        fl.close()
        return data
    finally:
        ssh_connection.close()


class InstanceInteropHelper(object):
    def __init__(self, instance):
        self.instance = instance
        self.execute_command = functools.partial(
            execute_command, ssh_connection=self.ssh_connection)
        self.write_file_to = functools.partial(
            write_file_to, ssh_connection=self.ssh_connection)
        self.read_file_from = functools.partial(
            read_file_from, ssh_connection=self.ssh_connection)

    @property
    def ssh_connection(self):
        return setup_ssh_connection(self.instance.hostname,
                                    self.instance.username,
                                    self.instance.private_key)
