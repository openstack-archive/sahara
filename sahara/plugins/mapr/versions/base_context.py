# Copyright (c) 2014, MapR Technologies
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import abc

import six

import sahara.plugins.mapr.util.config_utils as cu
import sahara.plugins.mapr.util.names as n
import sahara.plugins.utils as u


@six.add_metaclass(abc.ABCMeta)
class BaseContext(object):

    hive_version_config = 'Hive Version'
    oozie_version_config = 'Oozie Version'

    @abc.abstractmethod
    def get_cluster(self):
        return

    @abc.abstractmethod
    def is_m7_enabled(self):
        return

    @abc.abstractmethod
    def get_hadoop_version(self):
        return

    def get_linux_distro_version(self):
        return self.get_zk_instances()[0].remote().execute_command(
            'lsb_release -is', run_as_root=True)[1].rstrip()

    def get_install_manager(self):
        install_manager_map = {'Ubuntu': 'apt-get install --force-yes -y ',
                               'CentOS': 'yum install -y ',
                               'RedHatEnterpriseServer': 'yum install -y ',
                               'Suse': 'zypper '}
        return install_manager_map.get(self.get_linux_distro_version())

    def get_install_manager_version_separator(self):
        install_manager_map = {'Ubuntu': '=',
                               'CentOS': '-',
                               'RedHatEnterpriseServer': '-',
                               'Suse': ':'}
        return install_manager_map.get(self.get_linux_distro_version())

    def get_fs_instances(self):
        return u.get_instances(self.get_cluster(), n.FILE_SERVER)

    def get_zk_instances(self):
        return u.get_instances(self.get_cluster(), n.ZOOKEEPER)

    def get_zk_uris(self):
        mapper = lambda i: '%s' % i.management_ip
        return map(mapper, self.get_zk_instances())

    def get_cldb_instances(self):
        return u.get_instances(self.get_cluster(), n.CLDB)

    def get_cldb_uris(self):
        mapper = lambda i: '%s' % i.management_ip
        return map(mapper, self.get_cldb_instances())

    def get_cldb_uri(self):
        return 'maprfs:///'

    def get_rm_instance(self):
        return u.get_instance(self.get_cluster(), n.RESOURCE_MANAGER)

    def get_rm_port(self):
        return '8032'

    def get_rm_uri(self):
        port = self.get_rm_port()
        ip = self.get_rm_instance().management_ip
        return '%s:%s' % (ip, port) if port else ip

    def get_hs_instance(self):
        return u.get_instance(self.get_cluster(), n.HISTORY_SERVER)

    def get_hs_uri(self):
        return self.get_hs_instance().management_ip

    def get_oozie_instance(self):
        return u.get_instance(self.get_cluster(), n.OOZIE)

    def get_hive_metastore_instances(self):
        return u.get_instances(self.get_cluster(), n.HIVE_METASTORE)

    def get_hive_server2_instances(self):
        return u.get_instances(self.get_cluster(), n.HIVE_SERVER2)

    def get_oozie_uri(self):
        ip = self.get_oozie_instance().management_ip
        return 'http://%s:11000/oozie' % ip

    def get_roles_str(self, comp_list):
        component_list_str = 'mapr-core ' + ' '.join(['mapr-' + role + ' '
                                                      for role in comp_list])
        if 'HBase-Client' in comp_list:
            component_list_str = component_list_str.replace(
                'HBase-Client', 'hbase')
        if 'Oozie' in comp_list:
            component_list_str = component_list_str.replace(
                'Oozie', 'oozie' + self.get_oozie_version())
        if 'HiveMetastore' in comp_list:
            component_list_str = component_list_str.replace(
                'HiveMetastore', 'HiveMetastore' + self.get_hive_version())
        if 'HiveServer2' in comp_list:
            component_list_str = component_list_str.replace(
                'HiveServer2', 'HiveServer2' + self.get_hive_version())

        return component_list_str.lower()

    def user_exists(self):
        return

    def get_plain_instances(self):
        fs = self.get_fs_instances()
        zk = self.get_zk_instances()
        cldb = self.get_cldb_instances()
        zk_fs_cldb = zk + fs + cldb
        instances = u.get_instances(self.get_cluster())
        return [i for i in instances if i not in zk_fs_cldb]

    def get_configure_command(self):
        kargs = {'path': self.get_configure_sh_path(),
                 'cldb_nodes': ','.join(self.get_cldb_uris()),
                 'zk_nodes': ','.join(self.get_cldb_uris()),
                 'rm_node': self.get_rm_uri(),
                 'hs_node': self.get_hs_uri()}
        command = ('{path} -C {cldb_nodes} -Z {zk_nodes} -RM {rm_node}'
                   ' -HS {hs_node} -f').format(**kargs)
        if self.is_m7_enabled():
            command += ' -M7'
        if not self.user_exists():
            command += ' --create-user'
        return command

    def get_fs_wait_command(self):
        return '/tmp/waiting_script.sh'

    def get_disk_setup_command(self):
        return '/opt/mapr/server/disksetup -F /tmp/disk.list'

    def get_configure_sh_path(self):
        return '/opt/mapr/server/configure.sh'

    def get_oozie_version(self):
        configs = cu.get_cluster_configs(self.get_cluster())
        return (self.get_install_manager_version_separator()
                + configs[n.OOZIE][BaseContext.oozie_version_config] + '*')

    def get_hive_version(self):
        configs = cu.get_cluster_configs(self.get_cluster())
        return (self.get_install_manager_version_separator()
                + configs[n.HIVE][BaseContext.hive_version_config] + "*")

    def get_scripts(self):
        return
