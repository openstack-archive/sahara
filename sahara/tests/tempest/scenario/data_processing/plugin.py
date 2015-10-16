# Copyright (c) 2015 Red Hat, Inc.
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


import os

from tempest.test_discover import plugins

import sahara.tests.tempest.scenario.data_processing.config as sahara_config


class SaharaClientsScenarioPlugin(plugins.TempestPlugin):
    def load_tests(self):
        relative_test_dir = 'sahara/tests/tempest/scenario/data_processing'
        test_dir = os.path.dirname(os.path.abspath(__file__))
        top_level_dir = test_dir[:test_dir.find(relative_test_dir)-1]
        return test_dir, top_level_dir

    def register_opts(self, conf):
        # additional options in the data_processing section
        conf.register_opts(sahara_config.DataProcessingGroup,
                           'data-processing')

    def get_opt_lists(self):
        return [('data-processing', sahara_config.DataProcessingGroup)]
