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

import testtools

from sahara.service.edp.oozie.workflow_creator import workflow_factory as w_f
from sahara.utils import edp


class TestJobPossibleConfigs(testtools.TestCase):

    def test_possible_configs(self):
        res = w_f.get_possible_job_config(edp.JOB_TYPE_MAPREDUCE)
        sample_config_property = {
            'name': 'mapreduce.jobtracker.expire.trackers.interval',
            'value': '600000',
            'description': "Expert: The time-interval, in miliseconds, after "
                           "whicha tasktracker is declared 'lost' if it "
                           "doesn't send heartbeats."
        }
        self.assertIn(sample_config_property, res['job_config']["configs"])

        res = w_f.get_possible_job_config(edp.JOB_TYPE_HIVE)
        sample_config_property = {
            "description": "The serde used by FetchTask to serialize the "
                           "fetch output.",
            "name": "hive.fetch.output.serde",
            "value": "org.apache.hadoop.hive.serde2.DelimitedJSONSerDe"
        }
        self.assertIn(sample_config_property, res["job_config"]['configs'])
        res = w_f.get_possible_job_config("impossible_config")
        self.assertIsNone(res)
