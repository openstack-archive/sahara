# Copyright (c) 2013 Mirantis Inc.
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

import unittest2

from sahara.service.edp.workflow_creator import workflow_factory as w_f


class TestJobPossibleConfigs(unittest2.TestCase):

    def test_possible_configs(self):
        res = w_f.get_possible_job_config("MapReduce")
        sample_config_property = {
            'name': 'mapred.map.tasks',
            'value': '2',
            'description': 'The default number of map tasks per job.'
            'Ignored when mapred.job.tracker is "local".  '
        }
        self.assertIn(sample_config_property, res['job_config']["configs"])

        res = w_f.get_possible_job_config("Hive")
        sample_config_property = {
            "description": "The serde used by FetchTask to serialize the "
                           "fetch output.",
            "name": "hive.fetch.output.serde",
            "value": "org.apache.hadoop.hive.serde2.DelimitedJSONSerDe"
        }
        self.assertIn(sample_config_property, res["job_config"]['configs'])
        res = w_f.get_possible_job_config("impossible_config")
        self.assertIsNone(res)
