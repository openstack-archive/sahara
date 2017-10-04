# Copyright (c) 2015 Intel Corporation
# Copyright (c) 2015 ISPRAS
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

from sahara.plugins.cdh import abstractversionhandler as avm
from sahara.plugins.cdh.v5_9_0 import cloudera_utils
from sahara.plugins.cdh.v5_9_0 import config_helper
from sahara.plugins.cdh.v5_9_0 import deploy
from sahara.plugins.cdh.v5_9_0 import edp_engine
from sahara.plugins.cdh.v5_9_0 import images
from sahara.plugins.cdh.v5_9_0 import plugin_utils
from sahara.plugins.cdh.v5_9_0 import validation


class VersionHandler(avm.BaseVersionHandler):

    def __init__(self):
        super(VersionHandler, self).__init__()
        self.config_helper = config_helper.ConfigHelperV590()
        self.cloudera_utils = cloudera_utils.ClouderaUtilsV590()
        self.plugin_utils = plugin_utils.PluginUtilsV590()
        self.deploy = deploy
        self.edp_engine = edp_engine
        self.images = images
        self.validation = validation.ValidatorV590()
