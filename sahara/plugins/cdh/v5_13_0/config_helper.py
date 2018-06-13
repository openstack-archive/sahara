# Copyright (c) 2016 Mirantis Inc.
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

from sahara.plugins.cdh import config_helper as c_h
from sahara.plugins import provisioning as p
from sahara.utils import files as f


class ConfigHelperV5130(c_h.ConfigHelper):
    path_to_config = 'plugins/cdh/v5_13_0/resources/'

    CDH5_UBUNTU_REPO = (
        'deb [arch=amd64] http://archive.cloudera.com/cdh5'
        '/ubuntu/xenial/amd64/cdh trusty-cdh5.13.0 contrib'
        '\ndeb-src http://archive.cloudera.com/cdh5/ubuntu'
        '/xenial/amd64/cdh trusty-cdh5.13.0 contrib')

    DEFAULT_CDH5_UBUNTU_REPO_KEY_URL = (
        'http://archive.cloudera.com/cdh5/ubuntu'
        '/xenial/amd64/cdh/archive.key')

    CM5_UBUNTU_REPO = (
        'deb [arch=amd64] http://archive.cloudera.com/cm5'
        '/ubuntu/xenial/amd64/cm trusty-cm5.13.0 contrib'
        '\ndeb-src http://archive.cloudera.com/cm5/ubuntu'
        '/xenial/amd64/cm trusty-cm5.13.0 contrib')

    DEFAULT_CM5_UBUNTU_REPO_KEY_URL = (
        'http://archive.cloudera.com/cm5/ubuntu'
        '/xenial/amd64/cm/archive.key')

    CDH5_CENTOS_REPO = (
        '[cloudera-cdh5]'
        '\nname=Cloudera\'s Distribution for Hadoop, Version 5'
        '\nbaseurl=http://archive.cloudera.com/cdh5/redhat/6'
        '/x86_64/cdh/5.13.0/'
        '\ngpgkey = http://archive.cloudera.com/cdh5/redhat/6'
        '/x86_64/cdh/RPM-GPG-KEY-cloudera'
        '\ngpgcheck = 1')

    CM5_CENTOS_REPO = (
        '[cloudera-manager]'
        '\nname=Cloudera Manager'
        '\nbaseurl=http://archive.cloudera.com/cm5/redhat/6'
        '/x86_64/cm/5.13.0/'
        '\ngpgkey = http://archive.cloudera.com/cm5/redhat/6'
        '/x86_64/cm/RPM-GPG-KEY-cloudera'
        '\ngpgcheck = 1')

    DEFAULT_SWIFT_LIB_URL = (
        'https://repository.cloudera.com/artifactory/repo/org'
        '/apache/hadoop/hadoop-openstack/2.6.0-cdh5.13.0'
        '/hadoop-openstack-2.6.0-cdh5.13.0.jar')

    SWIFT_LIB_URL = p.Config(
        'Hadoop OpenStack library URL', 'general', 'cluster', priority=1,
        default_value=DEFAULT_SWIFT_LIB_URL,
        description=("Library that adds Swift support to CDH. The file"
                     " will be downloaded by VMs."))

    HIVE_SERVER2_SENTRY_SAFETY_VALVE = f.get_file_text(
        path_to_config + 'hive-server2-sentry-safety.xml')

    HIVE_METASTORE_SENTRY_SAFETY_VALVE = f.get_file_text(
        path_to_config + 'hive-metastore-sentry-safety.xml')

    SENTRY_IMPALA_CLIENT_SAFETY_VALVE = f.get_file_text(
        path_to_config + 'sentry-impala-client-safety.xml')

    def is_keytrustee_available(self):
        return False

    def __init__(self):
        super(ConfigHelperV5130, self).__init__()
        self.priority_one_confs = self._load_json(
            self.path_to_config + 'priority-one-confs.json')
        self._init_all_ng_plugin_configs()
