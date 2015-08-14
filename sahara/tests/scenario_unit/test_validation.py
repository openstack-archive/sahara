# Copyright (c) 2015 Mirantis Inc.
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

import testtools
import yaml

from sahara.tests.scenario import validation


class TestValidation(testtools.TestCase):
    def test_validation(self):
        with open("sahara/tests/scenario_unit/vanilla2_7_1.yaml",
                  "r") as yaml_file:
            config = yaml.load(yaml_file)
        self.assertIsNone(validation.validate(config))
