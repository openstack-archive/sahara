# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


class Distro(object):
    def __init__(self, name, internal_name, install_cmd, version_separator):
        self._name = name
        self._internal_name = internal_name
        self._install_command = install_cmd
        self._version_separator = version_separator

    @property
    def name(self):
        return self._name

    @property
    def internal_name(self):
        return self._internal_name

    @property
    def install_command(self):
        return self._install_command

    @property
    def version_separator(self):
        return self._version_separator

    def create_install_cmd(self, packages):
        s = self.version_separator

        def join_package_version(pv_item):
            p, v = pv_item if len(pv_item) > 1 else (pv_item[0], None)
            return p + s + v + '*' if v else p

        packages = ' '.join(map(join_package_version, packages))
        command = '%(install_cmd)s %(packages)s'
        args = {'install_cmd': self.install_command, 'packages': packages}
        return command % args


UBUNTU = Distro(
    name='Ubuntu',
    internal_name='Ubuntu',
    install_cmd='apt-get install --force-yes -y',
    version_separator='=',
)

CENTOS = Distro(
    name='CentOS',
    internal_name='CentOS',
    install_cmd='yum install -y',
    version_separator='-',
)

RHEL = Distro(
    name='RedHatEnterpriseServer',
    internal_name='RedHat',
    install_cmd='yum install -y',
    version_separator='-',
)

SUSE = Distro(
    name='Suse',
    internal_name='Suse',
    install_cmd='zypper',
    version_separator=':',
)


def get_all():
    return [UBUNTU, CENTOS, RHEL, SUSE]


def get(instance):
    with instance.remote() as r:
        name = r.get_os_distrib()
        for d in get_all():
            if d.internal_name.lower() in name:
                return d


def get_version(instance):
    with instance.remote() as r:
        version = r.get_os_version()
        return version
