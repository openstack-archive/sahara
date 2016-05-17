# Copyright (c) 2014 Mirantis Inc.
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

from sahara.i18n import _
from sahara.plugins import exceptions as ex


def _root(remote, cmd, **kwargs):
    return remote.execute_command(cmd, run_as_root=True, **kwargs)


def _get_os_distrib(remote):
    return remote.execute_command('lsb_release -is')[1].strip().lower()


def is_centos_os(remote):
    return _get_os_distrib(remote) == 'centos'


def is_ubuntu_os(remote):
    return _get_os_distrib(remote) == 'ubuntu'


def is_pre_installed_cdh(remote):
    code, out = remote.execute_command('ls /etc/init.d/cloudera-scm-server',
                                       raise_when_error=False)
    return code == 0


def start_cloudera_db(remote):
    _root(remote, 'service cloudera-scm-server-db start')
    # for Hive access
    hive_access_param = 'host metastore hive 0.0.0.0/0 md5'
    remote.append_to_file('/var/lib/cloudera-scm-server-db/data/pg_hba.conf',
                          hive_access_param, run_as_root=True)
    _root(remote, 'service cloudera-scm-server-db restart')


def start_manager(remote):
    _root(remote, 'service cloudera-scm-server start')


def configure_agent(remote, manager_address):
    remote.replace_remote_string('/etc/cloudera-scm-agent/config.ini',
                                 'server_host=.*',
                                 'server_host=%s' % manager_address)


def start_agent(remote):
    _root(remote, 'service cloudera-scm-agent start')


def install_packages(remote, packages, timeout=1800):
    distrib = _get_os_distrib(remote)
    if distrib == 'ubuntu':
        cmd = 'RUNLEVEL=1 apt-get install -y %s'
    elif distrib == 'centos':
        cmd = 'yum install -y %s'
    else:
        raise ex.HadoopProvisionError(
            _("OS on image is not supported by CDH plugin"))

    cmd = cmd % ' '.join(packages)
    _root(remote, cmd, timeout=timeout)


def update_repository(remote):
    if is_ubuntu_os(remote):
        _root(remote, 'apt-get update')
    if is_centos_os(remote):
        _root(remote, 'yum clean all')


def push_remote_file(remote, src, dst):
    cmd = 'curl %s -o %s' % (src, dst)
    _root(remote, cmd)


def add_ubuntu_repository(r, repo_list_url, repo_name):
    push_remote_file(r, repo_list_url,
                     '/etc/apt/sources.list.d/%s.list' % repo_name)


def write_ubuntu_repository(r, repo_content, repo_name):
    r.write_file_to('/etc/apt/sources.list.d/%s.list' % repo_name,
                    repo_content, run_as_root=True)


def add_apt_key(remote, key_url):
    cmd = 'wget -qO - %s | apt-key add -' % key_url
    _root(remote, cmd)


def add_centos_repository(r, repo_list_url, repo_name):
    push_remote_file(r, repo_list_url, '/etc/yum.repos.d/%s.repo' % repo_name)


def write_centos_repository(r, repo_content, repo_name):
    r.write_file_to('/etc/yum.repos.d/%s.repo' % repo_name,
                    repo_content, run_as_root=True)


def start_mysql_server(remote):
    _root(remote, 'service mysql start')
