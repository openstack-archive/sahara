# Copyright 2015 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from sahara import conductor  # noqa
from sahara.plugins import base as plugins_base
from sahara.utils import remote

try:
    import guestfs
except ImportError:
    raise Exception("The image packing API depends on the system package "
                    "python-libguestfs (and libguestfs itself.) Please "
                    "install these packages to proceed.")


LOG = None
CONF = None


# This is broken out to support testability
def set_logger(log):
    global LOG
    LOG = log


# This is broken out to support testability
def set_conf(conf):
    global CONF
    CONF = conf


# This is a local exception class that is used to exit routines
# in cases where error information has already been logged.
# It is caught and suppressed everywhere it is used.
class Handled(Exception):
    pass


class Context(object):
    '''Create a pseudo Context object

    Since this tool does not use the REST interface, we
    do not have a request from which to build a Context.
    '''
    def __init__(self, is_admin=False, tenant_id=None):
        self.is_admin = is_admin
        self.tenant_id = tenant_id


class ImageRemote(remote.TerminalOnlyRemote):

    def __init__(self, image_path, root_drive):
        guest = guestfs.GuestFS(python_return_dict=True)
        guest.add_drive_opts(image_path, format="qcow2")
        guest.set_network(True)
        self.guest = guest
        self.root_drive = root_drive

    def __enter__(self):
        self.guest.launch()
        if not self.root_drive:
            self.root_drive = self.guest.inspect_os()[0]
        self.guest.mount(self.root_drive, '/')
        try:
            cmd = "echo Testing sudo without tty..."
            self.execute_command(cmd, run_as_root=True)
        except RuntimeError:
            cmd = "sed -i 's/requiretty/!requiretty/' /etc/sudoers"
            self.guest.execute_command(cmd)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.guest.sync()
        self.guest.umount_all()
        self.guest.close()

    def execute_command(self, cmd, run_as_root=False, get_stderr=False,
                        raise_when_error=True, timeout=300):
        try:
            LOG.info("Issuing command: {cmd}".format(cmd=cmd))
            stdout = self.guest.sh(cmd)
            LOG.info("Received response: {stdout}".format(stdout=stdout))
            return 0, stdout
        except RuntimeError as ex:
            if raise_when_error:
                raise
            else:
                return 1, ex.message

    def get_os_distrib(self):
        return self.guest.inspect_get_distro(self.root_drive)

    def write_file_to(self, path, script, run_as_root):
        LOG.info("Writing script to : {path}".format(path=path))
        stdout = self.guest.write(path, script)
        return 0, stdout


def setup_plugins():
    plugins_base.setup_plugins()


def get_loaded_plugins():
    return plugins_base.PLUGINS.plugins


def get_plugin_arguments(plugin_name):
    """Gets plugin arguments, as a dict of version to argument list."""
    plugin = plugins_base.PLUGINS.get_plugin(plugin_name)
    versions = plugin.get_versions()
    return {version: plugin.get_image_arguments(version)
            for version in versions}


def pack_image(image_path, plugin_name, plugin_version, image_arguments,
               root_drive=None, test_only=False):
    with ImageRemote(image_path, root_drive) as image_remote:
        plugin = plugins_base.PLUGINS.get_plugin(plugin_name)
        plugin.pack_image(plugin_version, image_remote, test_only=test_only,
                          image_arguments=image_arguments)
