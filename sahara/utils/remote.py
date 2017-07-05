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

import abc

from oslo_config import cfg
import six

from sahara import exceptions as ex
from sahara.i18n import _

# These options are for SSH remote only
ssh_opts = [
    cfg.IntOpt('global_remote_threshold', default=100,
               help='Maximum number of remote operations that will '
                    'be running at the same time. Note that each '
                    'remote operation requires its own process to '
                    'run.'),
    cfg.IntOpt('cluster_remote_threshold', default=70,
               help='The same as global_remote_threshold, but for '
                    'a single cluster.'),
    cfg.StrOpt('proxy_command', default='',
               help='Proxy command used to connect to instances. If set, this '
               'command should open a netcat socket, that Sahara will use for '
               'SSH and HTTP connections. Use {host} and {port} to describe '
               'the destination. Other available keywords: {tenant_id}, '
               '{network_id}, {router_id}.'),
    cfg.BoolOpt('proxy_command_use_internal_ip', default=False,
                help='Force proxy_command usage to be consuming internal IP '
                'always, instead of management IP. Ignored if proxy_command '
                'is not set.')
]


CONF = cfg.CONF
CONF.register_opts(ssh_opts)


DRIVER = None


@six.add_metaclass(abc.ABCMeta)
class RemoteDriver(object):
    @abc.abstractmethod
    def setup_remote(self, engine):
        """Performs driver initialization."""

    @abc.abstractmethod
    def get_remote(self, instance):
        """Returns driver specific Remote."""

    @abc.abstractmethod
    def get_userdata_template(self):
        """Returns userdata template preparing instance to work with driver."""

    @abc.abstractmethod
    def get_type_and_version(self):
        """Returns engine type and version

         Result should be in the form 'type.major.minor'.
         """


@six.add_metaclass(abc.ABCMeta)
class TerminalOnlyRemote(object):

    @abc.abstractmethod
    def execute_command(self, cmd, run_as_root=False, get_stderr=False,
                        raise_when_error=True, timeout=300):
        """Execute specified command remotely using existing ssh connection.

        Return exit code, stdout data and stderr data of the executed command.
        """

    @abc.abstractmethod
    def get_os_distrib(self):
        """Returns the OS distribution running on the target machine."""


@six.add_metaclass(abc.ABCMeta)
class Remote(TerminalOnlyRemote):

    @abc.abstractmethod
    def get_neutron_info(self):
        """Returns dict which later could be passed to get_http_client."""

    @abc.abstractmethod
    def get_http_client(self, port, info=None):
        """Returns HTTP client for a given instance's port."""

    @abc.abstractmethod
    def close_http_session(self, port):
        """Closes cached HTTP session for a given instance's port."""

    @abc.abstractmethod
    def write_file_to(self, remote_file, data, run_as_root=False, timeout=120):
        """Create remote file and write the given data to it.

        Uses existing ssh connection.
        """

    @abc.abstractmethod
    def append_to_file(self, r_file, data, run_as_root=False, timeout=120):
        """Append the given data to remote file.

        Uses existing ssh connection.
        """

    @abc.abstractmethod
    def write_files_to(self, files, run_as_root=False, timeout=120):
        """Copy file->data dictionary in a single ssh connection."""

    @abc.abstractmethod
    def append_to_files(self, files, run_as_root=False, timeout=120):
        """Copy file->data dictionary in a single ssh connection."""

    @abc.abstractmethod
    def read_file_from(self, remote_file, run_as_root=False, timeout=120):
        """Read remote file from the specified host and return given data."""

    @abc.abstractmethod
    def replace_remote_string(self, remote_file, old_str, new_str,
                              timeout=120):
        """Replaces strings in remote file using sed command."""


def setup_remote(driver, engine):
    global DRIVER

    DRIVER = driver
    DRIVER.setup_remote(engine)


def get_remote_type_and_version():
    return DRIVER.get_type_and_version()


def _check_driver_is_loaded():
    if not DRIVER:
        raise ex.SystemError(_('Remote driver is not loaded. Most probably '
                               'you see this error because you are running '
                               'Sahara in distributed mode and it is broken.'
                               'Try running sahara-all instead.'))


def get_remote(instance):
    """Returns Remote for a given instance."""
    _check_driver_is_loaded()
    return DRIVER.get_remote(instance)


def get_userdata_template():
    """Returns userdata template as a string."""
    _check_driver_is_loaded()
    return DRIVER.get_userdata_template()
