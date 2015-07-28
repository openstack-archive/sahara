# Copyright (c) 2015 Intel Corp.
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

from sahara.utils import configs


class ConfigsTestCase(testtools.TestCase):

    def test_merge_configs(self):
        a = {
            'HDFS': {
                'param1': 'value1',
                'param2': 'value2'
            }
        }
        b = {
            'HDFS': {
                'param1': 'value3',
                'param3': 'value4'
            },
            'YARN': {
                'param5': 'value5'
            }
        }

        res = configs.merge_configs(a, b)
        expected = {
            'HDFS': {
                'param1': 'value3',
                'param2': 'value2',
                'param3': 'value4'
            },
            'YARN': {
                'param5': 'value5'
            }
        }
        self.assertEqual(expected, res)
