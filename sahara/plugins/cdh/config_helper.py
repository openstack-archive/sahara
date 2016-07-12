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

from oslo_serialization import jsonutils as json

from sahara.plugins import provisioning as p
from sahara.utils import files as f


class ConfigHelper(object):
    path_to_config = ''

    CDH5_REPO_URL = p.Config(
        'CDH5 repo list URL', 'general', 'cluster', priority=1,
        default_value="")

    CDH5_REPO_KEY_URL = p.Config(
        'CDH5 repo key URL (for debian-based only)', 'general', 'cluster',
        priority=1, default_value="")

    CM5_REPO_URL = p.Config(
        'CM5 repo list URL', 'general', 'cluster', priority=1,
        default_value="")

    CM5_REPO_KEY_URL = p.Config(
        'CM5 repo key URL (for debian-based only)', 'general', 'cluster',
        priority=1, default_value="")

    ENABLE_SWIFT = p.Config('Enable Swift', 'general', 'cluster',
                            config_type='bool', priority=1,
                            default_value=True)

    ENABLE_HBASE_COMMON_LIB = p.Config(
        'Enable HBase Common Lib', 'general', 'cluster', config_type='bool',
        priority=1, default_value=True)

    DEFAULT_SWIFT_LIB_URL = (
        'https://repository.cloudera.com/artifactory/repo/org'
        '/apache/hadoop/hadoop-openstack/2.3.0-cdh5.0.0'
        '/hadoop-openstack-2.3.0-cdh5.0.0.jar')

    DEFAULT_EXTJS_LIB_URL = 'http://sahara-files.mirantis.com/ext-2.2.zip'

    SWIFT_LIB_URL = p.Config(
        'Hadoop OpenStack library URL', 'general', 'cluster', priority=1,
        default_value=DEFAULT_SWIFT_LIB_URL,
        description=("Library that adds Swift support to CDH. The file"
                     " will be downloaded by VMs."))

    EXTJS_LIB_URL = p.Config(
        "ExtJS library URL", 'general', 'cluster', priority=1,
        default_value=DEFAULT_EXTJS_LIB_URL,
        description=("Ext 2.2 library is required for Oozie Web Console. "
                     "The file will be downloaded by VMs with oozie."))

    AWAIT_AGENTS_TIMEOUT = p.Config(
        'Await Cloudera agents timeout', 'general', 'cluster',
        config_type='int', priority=1, default_value=300, is_optional=True,
        description="Timeout for Cloudera agents connecting to"
                    " Coudera Manager, in seconds")

    AWAIT_MANAGER_STARTING_TIMEOUT = p.Config(
        'Timeout for Cloudera Manager starting', 'general', 'cluster',
        config_type='int', priority=1, default_value=300, is_optional=True,
        description='Timeout for Cloudera Manager starting, in seconds')

    def __new__(cls):
        # make it a singleton
        if not hasattr(cls, '_instance'):
            cls._instance = super(ConfigHelper, cls).__new__(cls)
            setattr(cls, '__init__', cls.decorate_init(cls.__init__))
        return cls._instance

    @classmethod
    def decorate_init(cls, f):
        """decorate __init__ to prevent multiple calling."""
        def wrap(*args, **kwargs):
            if not hasattr(cls, '_init'):
                f(*args, **kwargs)
                cls._init = True
        return wrap

    def __init__(self):
        self.ng_plugin_configs = []
        self.priority_one_confs = {}

    def _load_json(self, path_to_file):
        data = f.get_file_text(path_to_file)
        return json.loads(data)

    def _init_ng_configs(self, confs, app_target, scope):

        prepare_value = lambda x: x.replace('\n', ' ') if x else ""
        cfgs = []
        for cfg in confs:
            priority = 1 if cfg['name'] in self.priority_one_confs else 2
            c = p.Config(cfg['name'], app_target, scope, priority=priority,
                         default_value=prepare_value(cfg['value']),
                         description=cfg['desc'], is_optional=True)
            cfgs.append(c)

        return cfgs

    def _load_and_init_configs(self, filename, app_target, scope):
        confs = self._load_json(self.path_to_config + filename)
        cfgs = self._init_ng_configs(confs, app_target, scope)
        self.ng_plugin_configs += cfgs

        return cfgs

    def _get_ng_plugin_configs(self):
        return self.ng_plugin_configs

    def _get_cluster_plugin_configs(self):
        return [self.CDH5_REPO_URL, self.CDH5_REPO_KEY_URL, self.CM5_REPO_URL,
                self.CM5_REPO_KEY_URL, self.ENABLE_SWIFT,
                self.ENABLE_HBASE_COMMON_LIB, self.SWIFT_LIB_URL,
                self.EXTJS_LIB_URL, self.AWAIT_MANAGER_STARTING_TIMEOUT,
                self.AWAIT_AGENTS_TIMEOUT]

    def get_plugin_configs(self):
        cluster_wide = self._get_cluster_plugin_configs()
        ng_wide = self._get_ng_plugin_configs()
        return cluster_wide + ng_wide

    def _get_config_value(self, cluster, key):
        return cluster.cluster_configs.get(
            'general', {}).get(key.name, key.default_value)

    def get_cdh5_repo_url(self, cluster):
        return self._get_config_value(cluster, self.CDH5_REPO_URL)

    def get_cdh5_key_url(self, cluster):
        return self._get_config_value(cluster, self.CDH5_REPO_KEY_URL)

    def get_cm5_repo_url(self, cluster):
        return self._get_config_value(cluster, self.CM5_REPO_URL)

    def get_cm5_key_url(self, cluster):
        return self._get_config_value(cluster, self.CM5_REPO_KEY_URL)

    def is_swift_enabled(self, cluster):
        return self._get_config_value(cluster, self.ENABLE_SWIFT)

    def is_hbase_common_lib_enabled(self, cluster):
        return self._get_config_value(cluster,
                                      self.ENABLE_HBASE_COMMON_LIB)

    def get_swift_lib_url(self, cluster):
        return self._get_config_value(cluster, self.SWIFT_LIB_URL)

    def get_extjs_lib_url(self, cluster):
        return self._get_config_value(cluster, self.EXTJS_LIB_URL)
