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

from sahara.plugins.cdh import cloudera_utils as cu
from sahara.plugins.cdh.v5_13_0 import config_helper
from sahara.plugins.cdh.v5_13_0 import plugin_utils as pu
from sahara.plugins.cdh.v5_13_0 import validation


class ClouderaUtilsV5130(cu.ClouderaUtils):

    def __init__(self):
        cu.ClouderaUtils.__init__(self)
        self.pu = pu.PluginUtilsV5130()
        self.validator = validation.ValidatorV5130
        self.c_helper = config_helper.ConfigHelperV5130()

    def _load_version_specific_instance_configs(self, instance, default_conf):
        if instance.node_group.node_configs.get('HIVEMETASTORE', {}).get(
                'hive_enable_db_notification', None) is None:
            default_conf['HIVEMETASTORE']['hive_enable_db_notification'] = (
                'true')
